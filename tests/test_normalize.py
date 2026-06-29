from pipeline.normalize import (
    normalize_name,
    normalize_email,
    normalize_phone,
    normalize_date,
    normalize_skill,
    normalize_location
)

def test_normalize_name():
    assert normalize_name("priya sharma")[0] == "Priya Sharma"
    assert normalize_name("  P.   Sharma  ")[0] == "P. Sharma"
    assert normalize_name(None)[0] is None

def test_normalize_email():
    assert normalize_email("Priya.Sharma@Example.Com")[0] == "priya.sharma@example.com"
    assert normalize_email("  test@test.com  ")[0] == "test@test.com"

def test_normalize_phone():
    # E.164 test cases
    assert normalize_phone("+15550142323")[0] == "+15550142323"
    assert normalize_phone("(555) 014-2323")[0] == "+15550142323"
    assert normalize_phone("+91 98765 43210")[0] == "+919876543210"

def test_normalize_date():
    assert normalize_date("Jan 2020")[0] == "2020-01"
    assert normalize_date("2020/12")[0] == "2020-12"
    assert normalize_date("Present")[0] == "Present"

def test_normalize_skill():
    assert normalize_skill("js")[0] == "JavaScript"
    assert normalize_skill("react.js")[0] == "React"
    assert normalize_skill("python")[0] == "Python"
    assert normalize_skill("c++")[0] == "C++"

def test_normalize_location():
    loc = {"city": "San Francisco", "region": "CA", "country": "United States"}
    res, method = normalize_location(loc)
    assert res["city"] == "San Francisco"
    assert res["country"] == "US"
