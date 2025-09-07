import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Copy, FileText, AlertTriangle, Calendar, Link as LinkIcon, Image as ImageIcon, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

/**
 * Tank 옥션 페이지 파싱 결과 스키마
 */
type ParseResult = {
  source: "tank:detail" | "unknown";
  ok: boolean;
  fields: {
    appraisalPrice?: number;    // 감정가
    minBid?: number;           // 최저입찰가
    dividendDue?: string;      // 배분요구종기  
    landArea?: number;         // 토지면적
    buildingArea?: number;     // 건물면적
    usage?: string;            // 세부용도
    contact?: string;          // 담당부서/담당자/연락처
    [key: string]: any;
  };
  schedules: Array<{
    round?: number;
    open?: string;
    close?: string; 
    minBid?: number;
    _raw: string[];            // 원본 행 데이터
  }>;
  documents: Array<{
    text: string;
    href?: string;
    type: "doc" | "image";
  }>;
  riskFlags: string[];         // 리스크 플래그
  _debug: {
    isHtml: boolean;
    textLength: number;
    tableCount: number;
    linkCount: number;
  };
};

/**
 * HTML인지 텍스트인지 판단하는 휴리스틱
 */
const isHtmlContent = (content: string): boolean => {
  const htmlIndicators = [/<[^>]+>/g, /&[a-zA-Z]+;/g];
  return htmlIndicators.some(pattern => pattern.test(content.slice(0, 1000)));
};

/**
 * HTML을 Document로 파싱
 */
const parseToDocument = (content: string): Document => {
  if (!isHtmlContent(content)) {
    // 텍스트인 경우 <pre> 태그로 래핑
    const wrappedContent = `<html><body><pre>${content}</pre></body></html>`;
    return new DOMParser().parseFromString(wrappedContent, 'text/html');
  }
  return new DOMParser().parseFromString(content, 'text/html');
};

/**
 * 라벨로 값 추출 (th/td, dt/dd, 콜론 패턴)
 */
const getByLabel = (doc: Document, labels: string[]): string | null => {
  // 1. 테이블 th/td 패턴
  const cells = doc.querySelectorAll('th, td');
  for (const cell of cells) {
    const cellText = cell.textContent?.trim() || '';
    if (labels.some(label => cellText.includes(label))) {
      // 같은 행의 다음 셀
      const nextCell = cell.nextElementSibling;
      if (nextCell?.textContent?.trim()) {
        return nextCell.textContent.trim();
      }
      
      // 부모 행에서 마지막 td 찾기
      const row = cell.closest('tr');
      if (row) {
        const lastTd = row.querySelector('td:last-child');
        if (lastTd && lastTd !== cell && lastTd.textContent?.trim()) {
          return lastTd.textContent.trim();
        }
      }
    }
  }
  
  // 2. dt/dd 패턴
  const dts = doc.querySelectorAll('dt');
  for (const dt of dts) {
    const dtText = dt.textContent?.trim() || '';
    if (labels.some(label => dtText.includes(label))) {
      const dd = dt.nextElementSibling;
      if (dd?.tagName === 'DD' && dd.textContent?.trim()) {
        return dd.textContent.trim();
      }
    }
  }
  
  // 3. 콜론 패턴 (전체 텍스트에서)
  const fullText = doc.body?.textContent || '';
  for (const label of labels) {
    const regex = new RegExp(`${label}\\s*:?\\s*([^\\n\\r]+)`, 'i');
    const match = fullText.match(regex);
    if (match && match[1]?.trim()) {
      return match[1].trim();
    }
  }
  
  return null;
};

/**
 * 숫자 추출 (콤마 제거 후 파싱)
 */
const extractNumber = (text: string | null): number | undefined => {
  if (!text) return undefined;
  const cleaned = text.replace(/[^\d.-]/g, '');
  const num = parseFloat(cleaned);
  return isNaN(num) ? undefined : num;
};

/**
 * 입찰일정 테이블 파싱
 */
const parseScheduleTable = (doc: Document): ParseResult['schedules'] => {
  const schedules: ParseResult['schedules'] = [];
  
  const tables = doc.querySelectorAll('table');
  for (const table of tables) {
    // 헤더에 입찰/일정/최저 키워드가 있는 테이블 찾기
    const headerText = table.querySelector('thead, tr:first-child')?.textContent || '';
    if (!/입찰|일정|최저/i.test(headerText)) continue;
    
    const rows = table.querySelectorAll('tbody tr, tr:not(:first-child)');
    for (const row of rows) {
      const cells = Array.from(row.querySelectorAll('td, th'));
      const rawData = cells.map(cell => cell.textContent?.trim() || '');
      
      if (rawData.length < 2) continue; // 최소 2개 컬럼 필요
      
      // 날짜 패턴 찾기
      const datePattern = /20\d{2}-\d{2}-\d{2}\s*\d{2}:\d{2}/;
      const dates = rawData.filter(cell => datePattern.test(cell));
      
      // 금액 패턴 찾기  
      const pricePattern = /[\d,]+/;
      const prices = rawData.filter(cell => pricePattern.test(cell) && !datePattern.test(cell));
      
      schedules.push({
        open: dates[0] || undefined,
        close: dates[1] || undefined,
        minBid: prices.length > 0 ? extractNumber(prices[prices.length - 1]) : undefined,
        _raw: rawData
      });
    }
  }
  
  return schedules;
};

/**
 * 문서 링크 추출
 */
const extractDocuments = (doc: Document): ParseResult['documents'] => {
  const documents: ParseResult['documents'] = [];
  const docKeywords = ['감정평가서', '재산명세서', '현황', '명세', '평가'];
  
  // 문서 링크 추출 (최대 20개)
  const links = doc.querySelectorAll('a[href]');
  let docCount = 0;
  for (const link of links) {
    if (docCount >= 20) break;
    const linkText = link.textContent?.trim() || '';
    if (docKeywords.some(keyword => linkText.includes(keyword))) {
      documents.push({
        text: linkText,
        href: (link as HTMLAnchorElement).href,
        type: 'doc'
      });
      docCount++;
    }
  }
  
  // 이미지 추출 (최대 8개)
  const images = doc.querySelectorAll('img[src]');
  let imgCount = 0;
  for (const img of images) {
    if (imgCount >= 8) break;
    const alt = (img as HTMLImageElement).alt || '이미지';
    const src = (img as HTMLImageElement).src;
    documents.push({
      text: alt,
      href: src,
      type: 'image'
    });
    imgCount++;
  }
  
  return documents;
};

/**
 * 리스크 플래그 추출
 */
const extractRiskFlags = (doc: Document): string[] => {
  const flags: string[] = [];
  const fullText = doc.body?.textContent || '';
  
  const patterns = [
    { regex: /지분|공유지분/i, flag: '지분물건' },
    { regex: /대지권\s*없음|대지권 미등기/i, flag: '대지권 없음' },
    { regex: /건물만\s*매각/i, flag: '건물만 매각' }
  ];
  
  for (const { regex, flag } of patterns) {
    if (regex.test(fullText)) {
      flags.push(flag);
    }
  }
  
  return flags;
};

/**
 * 메인 파싱 함수
 */
const parseTankContent = (detailContent: string, sideContent?: string): ParseResult => {
  try {
    const detailDoc = parseToDocument(detailContent);
    const sideDoc = sideContent ? parseToDocument(sideContent) : null;
    
    // 핵심 필드 추출 (사이드 패널 우선)
    const getField = (labels: string[]) => {
      const sideValue = sideDoc ? getByLabel(sideDoc, labels) : null;
      const detailValue = getByLabel(detailDoc, labels);
      return sideValue || detailValue;
    };
    
    const fields = {
      appraisalPrice: extractNumber(getField(['감정가', '감정가격', '평가가'])),
      minBid: extractNumber(getField(['최저입찰가', '최저가', '최저가격'])),
      dividendDue: getField(['배분요구종기', '배당요구종기']),
      landArea: extractNumber(getField(['토지면적'])),
      buildingArea: extractNumber(getField(['건물면적', '전용면적', '전유면적'])),
      usage: getField(['세부용도', '용도', '종류']),
      contact: getField(['담당부서', '담당자', '연락처'])
    };
    
    // 입찰일정 추출
    const detailSchedules = parseScheduleTable(detailDoc);
    const sideSchedules = sideDoc ? parseScheduleTable(sideDoc) : [];
    const schedules = [...detailSchedules, ...sideSchedules];
    
    // 최저입찰가 폴백 (일정표에서 최솟값)
    if (!fields.minBid && schedules.length > 0) {
      const minBids = schedules.map(s => s.minBid).filter(Boolean) as number[];
      if (minBids.length > 0) {
        fields.minBid = Math.min(...minBids);
      }
    }
    
    // 문서/이미지 추출
    const detailDocs = extractDocuments(detailDoc);
    const sideDocs = sideDoc ? extractDocuments(sideDoc) : [];
    const documents = [...detailDocs, ...sideDocs];
    
    // 리스크 플래그
    const detailFlags = extractRiskFlags(detailDoc);
    const sideFlags = sideDoc ? extractRiskFlags(sideDoc) : [];
    const riskFlags = Array.from(new Set([...detailFlags, ...sideFlags]));
    
    return {
      source: 'tank:detail',
      ok: true,
      fields,
      schedules,
      documents,
      riskFlags,
      _debug: {
        isHtml: isHtmlContent(detailContent),
        textLength: detailContent.length,
        tableCount: detailDoc.querySelectorAll('table').length,
        linkCount: detailDoc.querySelectorAll('a').length
      }
    };
    
  } catch (error) {
    return {
      source: 'unknown',
      ok: false,
      fields: {},
      schedules: [],
      documents: [],
      riskFlags: [],
      _debug: {
        isHtml: false,
        textLength: 0,
        tableCount: 0,
        linkCount: 0
      }
    };
  }
};

/**
 * Tank Parser 메인 컴포넌트
 */
const TankParser: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [detailContent, setDetailContent] = useState('');
  const [sideContent, setSideContent] = useState('');
  const [autoParse, setAutoParse] = useState(true);
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
  const [activeTab, setActiveTab] = useState('detail');
  
  const modalTextareaRef = useRef<HTMLTextAreaElement>(null);
  const detailTextareaRef = useRef<HTMLTextAreaElement>(null);
  const sideTextareaRef = useRef<HTMLTextAreaElement>(null);

  // Alt+A 전역 단축키
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.altKey && e.key === 'a') {
        e.preventDefault();
        setIsModalOpen(true);
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  // 모달 포커스
  useEffect(() => {
    if (isModalOpen && modalTextareaRef.current) {
      setTimeout(() => modalTextareaRef.current?.focus(), 100);
    }
  }, [isModalOpen]);

  // 파싱 실행
  const executeParse = useCallback(() => {
    if (!detailContent.trim()) {
      toast.error('상세 내용을 입력해주세요');
      return;
    }
    
    const result = parseTankContent(detailContent, sideContent || undefined);
    setParseResult(result);
    
    if (result.ok) {
      toast.success('파싱 완료!');
    } else {
      toast.error('파싱 실패');
    }
  }, [detailContent, sideContent]);

  // 자동 파싱
  useEffect(() => {
    if (autoParse && detailContent.trim()) {
      const timeoutId = setTimeout(executeParse, 500);
      return () => clearTimeout(timeoutId);
    }
  }, [detailContent, sideContent, autoParse, executeParse]);

  // 모달에서 Enter로 파싱
  const handleModalKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || !e.shiftKey)) {
      e.preventDefault();
      const content = (e.target as HTMLTextAreaElement).value;
      setDetailContent(content);
      setIsModalOpen(false);
      if (!autoParse) {
        executeParse();
      }
    }
  };

  // 붙여넣기 처리
  const handlePaste = (setter: (value: string) => void) => (e: React.ClipboardEvent) => {
    const pastedText = e.clipboardData.getData('text');
    setter(pastedText);
  };

  // JSON 복사
  const copyJson = () => {
    if (parseResult) {
      navigator.clipboard.writeText(JSON.stringify(parseResult, null, 2));
      toast.success('JSON 복사됨');
    }
  };

  // 초기화
  const resetAll = () => {
    setDetailContent('');
    setSideContent('');
    setParseResult(null);
    toast.success('초기화됨');
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* 헤더 */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2">Tank 옥션 파서</h1>
        <p className="text-muted-foreground">
          Alt+A로 빠른 입력 | 페이지 HTML/텍스트 붙여넣기로 자동 파싱
        </p>
      </div>

      {/* 컨트롤 패널 */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center space-x-2">
                <Switch
                  id="auto-parse"
                  checked={autoParse}
                  onCheckedChange={setAutoParse}
                />
                <label htmlFor="auto-parse" className="text-sm font-medium">
                  붙여넣기 시 자동 파싱
                </label>
              </div>
            </div>
            
            <div className="flex gap-2">
              <Button 
                variant="outline" 
                onClick={() => setIsModalOpen(true)}
                className="gap-2"
              >
                <FileText className="w-4 h-4" />
                빠른 입력 (Alt+A)
              </Button>
              <Button 
                variant="outline" 
                onClick={resetAll}
                className="gap-2"
              >
                <Trash2 className="w-4 h-4" />
                초기화
              </Button>
              <Button 
                onClick={executeParse}
                disabled={!detailContent.trim()}
                className="gap-2"
              >
                파싱 실행
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 입력 탭 */}
      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>입력</CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="detail">상세 HTML/텍스트</TabsTrigger>
                <TabsTrigger value="side">옆 패널 (선택)</TabsTrigger>
              </TabsList>
              
              <TabsContent value="detail" className="mt-4">
                <Textarea
                  ref={detailTextareaRef}
                  value={detailContent}
                  onChange={(e) => setDetailContent(e.target.value)}
                  onPaste={handlePaste(setDetailContent)}
                  placeholder="Tank 상세페이지 HTML 또는 텍스트를 붙여넣으세요..."
                  className="min-h-[300px] font-mono text-sm"
                />
              </TabsContent>
              
              <TabsContent value="side" className="mt-4">
                <Textarea
                  ref={sideTextareaRef}
                  value={sideContent}
                  onChange={(e) => setSideContent(e.target.value)}
                  onPaste={handlePaste(setSideContent)}
                  placeholder="옆 패널 문서 HTML (선택사항)..."
                  className="min-h-[300px] font-mono text-sm"
                />
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* 결과 패널 */}
        <div className="space-y-6">
          {parseResult && (
            <>
              {/* 핵심 추출 */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    {parseResult.ok ? (
                      <div className="w-2 h-2 bg-green-500 rounded-full" />
                    ) : (
                      <div className="w-2 h-2 bg-red-500 rounded-full" />
                    )}
                    핵심 추출
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* 필드 카드 */}
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <div className="text-muted-foreground">감정가</div>
                      <div className="font-medium">
                        {parseResult.fields.appraisalPrice?.toLocaleString() || '-'}
                      </div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">최저입찰가</div>
                      <div className="font-medium">
                        {parseResult.fields.minBid?.toLocaleString() || '-'}
                      </div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">배분요구종기</div>
                      <div className="font-medium">
                        {parseResult.fields.dividendDue || '-'}
                      </div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">면적</div>
                      <div className="font-medium">
                        {parseResult.fields.buildingArea || parseResult.fields.landArea || '-'}
                      </div>
                    </div>
                  </div>

                  {/* 리스크 플래그 */}
                  {parseResult.riskFlags.length > 0 && (
                    <div>
                      <div className="text-sm text-muted-foreground mb-2">리스크 플래그</div>
                      <div className="flex flex-wrap gap-2">
                        {parseResult.riskFlags.map((flag, idx) => (
                          <Badge key={idx} variant="destructive" className="gap-1">
                            <AlertTriangle className="w-3 h-3" />
                            {flag}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 입찰 일정 */}
                  {parseResult.schedules.length > 0 && (
                    <div>
                      <div className="text-sm text-muted-foreground mb-2 flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        입찰 일정
                      </div>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>시작</TableHead>
                            <TableHead>종료</TableHead>
                            <TableHead>최저가</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {parseResult.schedules.map((schedule, idx) => (
                            <TableRow key={idx}>
                              <TableCell className="font-mono text-xs">
                                {schedule.open || '-'}
                              </TableCell>
                              <TableCell className="font-mono text-xs">
                                {schedule.close || '-'}
                              </TableCell>
                              <TableCell>
                                {schedule.minBid?.toLocaleString() || '-'}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}

                  {/* 문서 링크 */}
                  {parseResult.documents.length > 0 && (
                    <div>
                      <div className="text-sm text-muted-foreground mb-2">관련 문서</div>
                      <div className="space-y-1 max-h-32 overflow-y-auto">
                        {parseResult.documents.map((doc, idx) => (
                          <div key={idx} className="flex items-center gap-2 text-xs">
                            {doc.type === 'doc' ? (
                              <LinkIcon className="w-3 h-3 text-blue-500" />
                            ) : (
                              <ImageIcon className="w-3 h-3 text-green-500" />
                            )}
                            <span className="truncate">{doc.text}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* JSON 결과 */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    JSON 결과
                    <Button size="sm" variant="outline" onClick={copyJson} className="gap-1">
                      <Copy className="w-3 h-3" />
                      복사
                    </Button>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="text-xs bg-muted p-3 rounded overflow-auto max-h-64">
                    {JSON.stringify(parseResult, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>

      {/* 빠른 입력 모달 */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle>빠른 입력</DialogTitle>
          </DialogHeader>
          <Textarea
            ref={modalTextareaRef}
            onKeyDown={handleModalKeyDown}
            placeholder="Tank 페이지 내용을 붙여넣고 Enter를 누르세요..."
            className="min-h-[400px] font-mono text-sm"
          />
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setIsModalOpen(false)}>
              취소
            </Button>
            <Button onClick={() => {
              const content = modalTextareaRef.current?.value || '';
              setDetailContent(content);
              setIsModalOpen(false);
            }}>
              적용
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TankParser;