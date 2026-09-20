import requests

url = "https://welfare-1gs5.onrender.com/transcribe"
file_path = "C:/Users/dudql/OneDrive/문서/project/imagin_project_test/code/back/serverchecking/speak.m4a"

# 1. 파일을 바이너리 읽기 모드('rb')로 엽니다.
with open(file_path, "rb") as f:
    # 2. 백엔드 변수명인 'audio_file'을 키(Key)값으로 맞춥니다.
    files = {"audio_file": f}
    
    # 3. params가 아닌 'files' 매개변수로 택배를 쏩니다.
    response = requests.post(url, files=files)

# 4. JSON 형태로 예쁘게 결과 확인
print(response.status_code)
print(response.json())