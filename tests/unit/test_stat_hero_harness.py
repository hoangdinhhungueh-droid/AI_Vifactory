import pytest
from app.services.master_scene_sheet import extract_stat_hero_from_text

test_cases = [
    ("Chi phí ước tính 620 billion won trong hồ sơ.", "620B WON"),
    ("Dự án yêu cầu ₩620B vốn cam kết.", "₩620B"),
    ("Dự án trị giá ₩620 billion.", "₩620B"),
    ("₩620 billion won cần thiết.", "₩620B"),
    ("Cơ chế 620-billion-won được ghi nhận.", "620B WON"),
    ("Six hundred twenty billion won: allegedly.", "620B WON"),
    ("Chi phí 620 tỷ won.", "620B WON"),
    ("Chi phí 620 triệu won.", "620M WON"),
    ("Tổng vốn 620조원.", "620조 WON"),
    ("Khoản cam kết 620억원.", "620억 WON"),
    ("Thời hạn khai trương ấn định năm 2029.", "2029"),
    ("Năm 2016 chính phủ lựa chọn Gimhae.", "2016"),
    ("Đạo luật thông qua ngày 26 tháng 2 năm 2021.", "2021"),
    ("Cuộc bầu cử diễn ra sau six weeks.", "6 WEEKS"),
    ("Khung thời gian cấp bách 48 hours.", "48 HOURS"),
    ("Thời gian 24 hrs.", "24 HOURS"),
    ("Thời gian 30 days.", "30 DAYS"),
    ("Khoản lỗ €500M của dự án.", "€500M"),
    ("Khoản lỗ €500 billion.", "€500B"),
    ("Tổng vốn 500 billion euros.", "€500B"),
    ("Tổng vốn 500 tỷ EUR.", "€500B"),
    ("Tổng vốn ¥123B tại Tokyo.", "¥123B"),
    ("Chi phí ¥123 billion.", "¥123B"),
    ("Chi phí 123 billion yen.", "¥123B"),
    ("Chi phí 123 tỷ yen.", "¥123B"),
    ("Doanh thu 123 tỷ đồng.", "123B VND"),
    ("Doanh thu 123 triệu VND.", "123M VND"),
    ("Chi phí 123k VND.", "123K VND"),
    ("Giá trị hợp đồng đạt $123 tỷ.", "$123 tỷ"),
    ("Chi phí $500M thất thoát.", "$500M"),
    ("Dự án $123B.", "$123B"),
    ("Dự án $123 billion.", "$123B"),
    ("Dự án 123 billion USD.", "$123B"),
    ("Dự án 123B USD.", "$123B"),
    ("Dự án 123 billion dollars.", "$123B"),
    ("Tăng trưởng vượt 85% chỉ số.", "85%"),
    ("Tăng trưởng 85 percent.", "85%"),
    ("Tăng trưởng 85 phần trăm.", "85%"),
    ("Tỷ lệ -12.5% sụt giảm.", "-12.5%"),
]


@pytest.mark.parametrize("inp,expected", test_cases)
def test_all_stat_hero_regex_cases(inp, expected):
    """Verifies that extract_stat_hero_from_text handles comprehensive cross-currency and temporal cases."""
    assert extract_stat_hero_from_text(inp) == expected
