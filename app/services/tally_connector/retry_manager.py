import time
from .logger import tally_logger

class RetryManager:
    """Manages execution retries with backoff for network/Tally HTTP requests."""
    
    @staticmethod
    def execute_with_retry(func, max_retries=3, initial_delay=1.0, backoff_factor=2.0, description="Operation"):
        delay = initial_delay
        last_exception = None
        
        for attempt in range(1, max_retries + 1):
            try:
                result = func()
                if attempt > 1:
                    tally_logger.info(f"✅ {description} succeeded on attempt {attempt}/{max_retries}.")
                return result
            except Exception as ex:
                last_exception = ex
                tally_logger.warning(f"⚠️ {description} failed (Attempt {attempt}/{max_retries}): {str(ex)}")
                if attempt < max_retries:
                    time.sleep(delay)
                    delay *= backoff_factor
                    
        tally_logger.error(f"❌ {description} failed after {max_retries} retries.")
        raise last_exception
