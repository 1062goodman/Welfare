pip install -r requirements.txt
명령어로 가상환경 설정

.env 파일 만들어서 key 같은변수 설정해줘야 하는데, key는 그냥 올리면 안되서 따로 공유할 방법 찾아보겠습니다. 

당초에 graph db, vector db 둘을 따로 관리하기로 했는데 최신버전 neo4j에서 벡터기능을 포함합니다. 결국에 neo4j하나만 써서 가능하게 됐습니다.



(1). db
    -1 dataExtraction.py 실행 시키면 공공데이터 api로 데이터를 받고 example.xml 생성.
    -2 parsing.py은 xml파일을 바탕으로 json파일 생성.
    -3 parsing_crawl.py은 json파일을 바탕으로 복지로 웹에 들어가 상세데이터(지원대상, 서비스 내용, 신첩방법)크롤링
    -4 db.py 로 neo4j인스턴스에 연결


(2). chat
    -1 아직 테스트중입니다.








==================================================
수정해야 할것들
- 데이터 정리를 위해 일단 대충 만듦. 파이프라인에 맞게 기능 나눠야함
- dataExtraction 코드가 공공데이터 포털api 처리에 맞춰짐. 다른 api도 처리할수 있게 유연하게 바꿔야함.

- 앱을 만들때 참고하면 좋을만한것들
    -모바일 애플리케이션 콘텐츠 접근성 지침 2.0 (국가표준 KS X 3253) https://webwatch.or.kr/MA/020201.html?MenuCD=220
    -고령자 친화적 모바일 금융앱 구성 지침 https://www.fsc.go.kr/no010101/77426
    -디지털 정부서비스 UI/UX 가이드라인 https://v04.krds.go.kr/guide/index.html
    