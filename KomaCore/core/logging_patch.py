# core/logging_patch.py
import logging, re
SENSITIVE = re.compile(r"(x-api-key|authorization)", re.I)
class Redact(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, dict):
            record.args = {k: ("*****" if SENSITIVE.search(k or "") else v) for k,v in record.args.items()}
        return True
logging.getLogger("uvicorn.access").addFilter(Redact())