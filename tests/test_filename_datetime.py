from datetime import datetime

def test_filename_datetime():
    now = datetime.now()
    filename = f"test_{now.strftime('%Y-%m-%d')}.csv"
    assert filename.startswith("test_")
    assert filename.endswith(".csv")
    # kiểm tra định dạng ngày tháng
    date_str = filename[5:-4]
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        assert False, f"Định dạng ngày tháng không hợp lệ: {date_str}"
    
    print(f"Generated filename: {filename}")
        
test_filename_datetime()