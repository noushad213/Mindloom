import pytest

from app.services.canonical_url import canonical_url


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("HTTPS://WWW.Example.COM:443/a/?utm_source=x&fbclid=y&id=5&gclid=z&mc_cid=a&ref=r#part", "https://example.com/a?id=5"),
        ("http://www.example.com:80/a///?b=2&a=1", "http://example.com/a?a=1&b=2"),
        ("https://www.bücher.de/", "https://xn--bcher-kva.de"),
    ],
)
def test_canonical_url(source, expected):
    assert canonical_url(source) == expected


@pytest.mark.parametrize("source", ["chrome://settings", "file:///tmp/a", "javascript:alert(1)", "not-a-url"])
def test_canonical_url_rejects_non_http(source):
    with pytest.raises(ValueError):
        canonical_url(source)
