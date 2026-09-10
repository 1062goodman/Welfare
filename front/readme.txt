워크디렉토리의 주소는 ascii로만 이루어져야함 (한국어, 한자 안됨)
워크디렉토리의 주소는 최대한 얕고 짧아야함 (예:C:\dev\code.... 총 글자 길이가 200자가 넘지 않게) (C:\develelapsfjk\imaginaryproject\asd\adasdf\code\... 이러면 안됨)

안드로이드 -----
1. 
스튜디오 설치
https://developer.android.com/studio?hl=ko 

jdk 설치
https://adoptium.net/temurin/releases/?version=17

2.
환경변수 만들기
변수이름: ANDROID_HOME
변수 값: C:\Users\사용자\AppData\Local\Android\Sdk (스튜디오 sdk가 설치된 곳. 다를수 있음)

path에 경로 두 개 추가
%ANDROID_HOME%\platform-tools
%ANDROID_HOME%\emulator

java 환경변수 만들기
변수이름: JAVA_HOME
변수 값: C:\Program Files\Eclipse Adoptium\jdk-17.0.20.101-hotspot (jdk가 설치된 곳. 다를수 있음)

path에 경로 한 개 추가
%JAVA_HOME%\bin

3.
android studio에서 
tools / SDK Manager (More Actions > SDK Manager) 에서 설치:
- SDK Platforms: 프로젝트 요구 API 레벨 (android/build.gradle의 compileSdk 확인)
- SDK Tools: NDK (Side by side), CMake, Android SDK Build-Tools, Command-line Tools


Gradle JVM 설정 (Settings > Build, Execution, Deployment > Build Tools > Gradle):
- Gradle JVM을 17로 설정 (JAVA_HOME과 별개로, Android Studio 안에서 직접 빌드할 때 필요)

(readme 폴더 안에 사진 참조)


4.
컴파일 하기 위해 폴더를 이동시켜주고 ,
cd front/welfare-chat-app

node_modules 설치
npm install

기종에 맞게 컴파일
npx expo run:android 
or
npx expo run:ios


5. 
실행 

모바일 (expo go 필요)
- npx expo start 
or 
-npm start

가상환경 (xcode이나 android studio 필요)
- npm run android
- npm run ios # you need to use macOS to build the iOS project - use the Expo app if you need to do iOS development without a Mac
- npm run web

