# ⚠️ LỖI: Python DLL không load được

## VẤN ĐỀ
Binary `observathon-sim.exe` cần Python 3.12 runtime nhưng bị lỗi:
```
Failed to load Python DLL 'python312.dll'
LoadLibrary: Invalid access to memory location.
```

## NGUYÊN NHÂN
- Binary được build bằng PyInstaller cần Visual C++ Runtime
- Windows của bạn thiếu hoặc có version cũ của Visual C++ Redistributable

## ✅ GIẢI PHÁP (LÀM NGAY)

### Bước 1: Download Visual C++ Redistributable
Mở link này trong browser và download:
```
https://aka.ms/vs/17/release/vc_redist.x64.exe
```

### Bước 2: Cài đặt
1. Double-click file `vc_redist.x64.exe` vừa download
2. Click "Install" hoặc "Repair" nếu đã có
3. Đợi cài đặt xong
4. **RESTART MÁY** (quan trọng!)

### Bước 3: Chạy lại
Sau khi restart, chạy:
```bash
run_sim.bat
```

## ⚡ NẾU VẪN KHÔNG ĐƯỢC

### Option A: Dùng Python trực tiếp
Nếu có source code của simulator:
```bash
pip install openai
python observathon_sim.py --config solution\config.json ...
```

### Option B: Liên hệ Instructor
- Yêu cầu binary version khác
- Hoặc yêu cầu source code để chạy với Python

## 📝 GHI CHÚ
File .env và các solution files (wrapper.py, config.json, prompt.txt) đã được chuẩn bị SẴN SÀNG.
Chỉ cần fix binary là có thể chạy ngay!
