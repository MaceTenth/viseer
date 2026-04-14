class BrowserFallback:
    def fetch_and_extract(self, url: str):
        raise NotImplementedError("Browser fallback is optional in v1.")
