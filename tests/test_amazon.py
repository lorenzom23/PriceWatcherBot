from scrapers.sites.amazon import AmazonScraper

scraper = AmazonScraper()


def test_extract_price_italian_format():
    assert scraper._extract_price("1.313,49€") == 1313.49


def test_extract_price_simple_comma():
    assert scraper._extract_price("135,22 €") == 135.22


def test_extract_price_us_format():
    assert scraper._extract_price("€1,299.00") == 1299.0


def test_can_handle_amazon():
    assert scraper.can_handle("https://www.amazon.it/dp/B01") is True


def test_can_handle_short_domain():
    assert scraper.can_handle("https://amzn.to/abc") is True


def test_can_handle_rejects_lookalike_domain():
    assert scraper.can_handle("https://amazon.evil.com/x") is False


def test_can_handle_rejects_other_site():
    assert scraper.can_handle("https://www.ebay.it/x") is False
