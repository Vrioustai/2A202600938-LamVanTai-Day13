# LỖI: Python DLL Load Failed

## NGUYÊN NHÂN
Binary `observathon-sim.exe` cần Python 3.12 DLL nhưng bị lỗi load trên hệ thống Windows của bạn.

## GIẢI PHÁP

### Option 1: Cài Visual C++ Redistributable (RECOMMENDED)
1. Download và cài đặt Microsoft Visual C++ 2015-2022 Redistributable:
   - 64-bit: https://aka.ms/vs/17/release/vc_redist.x64.exe
2. Restart máy
3. Chạy lại `run_sim.bat`

### Option 2: Cài Python 3.12
1. Download Python 3.12 từ https://www.python.org/downloads/
2. Khi cài, check ✅ "Add Python to PATH"
3. Sau khi cài xong, chạy lại binary

### Option 3: Kiểm tra Antivirus
- Antivirus có thể block DLL load
- Tạm tắt antivirus hoặc thêm exception cho folder này

### Option 4: Chạy từ Source Code (nếu các cách trên fail)
Nếu binary không chạy được, bạn có thể:
1. Cài Python 3.10+ và pip install openai
2. Yêu cầu instructor chạy từ source thay vì binary

## KIỂM TRA NHANH
Mở CMD và chạy:
```
python --version
```

Nếu không có Python, cài Python 3.12 trước.
