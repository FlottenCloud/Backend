# 오픈소스 클라우드 플랫폼을 이용한 사용자 맞춤형 가상머신 관리 시스템
## 1. 프로젝트 소개

최근 언택트 시대가 도래하면서 물리적 인프라를 직접 구축하지 않고도 컴퓨팅 자원에 접근할 수 있게 하는 클라우드 컴퓨팅이 각광받고 있다. 이러한 시대에 발맞춰 많은 클라우드 벤더들은 사용자에게 여러 유형의 클라우드 기반 서비스를 제공하고 있고, 클라우드 사용자들은 각자 다양한 목적과 용도로 이러한 서비스를 사용하고 있다. 그 중에서도 클라우드를 통해 사용자 각자의 요구에 알맞은 IT 인프라 자원을 이용하려는 사용자가 늘고 있다. 
하지만 사용자가 클라우드 컴퓨팅을 활용하기 위해서는 관련 용어 및 가상머신에 대한 전문적인 지식이 요구되므로 클라우드 관련 전문 지식이 부족한 사용자는 가상머신에 대한 설정을 잘 다루지 못하는 문제가 생긴다. 또한 사용자의 요구에 부합하는 가상머신을 생성하기 위해서 하드웨어, 소프트웨어 등에 대한 요구사항을 받아들이고 처리할 수 있는 구조도 지원되어야 한다. 
이와 더불어 클라우드 인프라 구축 후에 발생하는 관리적 측면의 어려움이 있다. 사용자의 클라우드 자원 활용에 따른 변경이 있을 경우 클라우드 자원의 활용도가 달라지게 되므로, 이를 처리하는 방안과 구조가 필요하다. 또한 갑작스러운 정전이나 재해 등과 같은 외부 요인 혹은 시스템 자체 결함 등의 내부 요인으로 클라우드 시스템에 장애가 생기는 경우, 클라우드 사용자가 장애발생에 유연하게 대처하는 것도 어려운 점 중 하나이다. 
따라서 본 과제는 사용자의 요구사항을 입력 받아 클라우드 가상머신 생성 시 필요한 설정, 요구 사항의 변경이 있을 시 가상머신의 업데이트, 재해발생 시 가상머신의 재해 복구를 지원하는 통합적인 가상 머신 관리 시스템 구현을 목표로 한다.

## 2. 팀 소개

201624406 고준성 kjs41680@gmail.com <br/> 
201624444 김영후 eagle7449@pusan.ac.kr <br/> 
201624540 이봉훈 drok02@naver.com <br/> 

## 3. 구성도
<img width="900" alt="그림1" src="https://user-images.githubusercontent.com/65642745/195553816-083954dc-9469-4881-a65b-a867bc17d46a.png">

## 4. 소개 및 시연 영상 
 시연 영상 주소
  https://www.youtube.com/watch?v=tqY4hYAoPsE
   
   
## 5. 사용법
---- cloudmanager part ----
1. In cloudmanager(main) directory -> pip install -r requirements.txt
2. In cloudmanager(project) directory in cloudmanager(main) -> settings.py의 맨 밑 Amazon S3 section에서 user의 access key, secret access key 작성
3. openstack_controller.py, cloudstack_controller.py in cloudmanager(main) directory, updater.py in openstack directory in cloudmanager(main) directory에서 오픈스택 서버와 클라우드스택의 서버 ip, 각 컴포넌트 별 id 등 작성
4. 각 app directory(accounts, openstack, cloudstack, infosender) 내에 migrations directory 생성 후 directory 내에 __init__.py(빈 파일) 생성
5. 1) python manage.py makemigrations / 2) python manage.py migrate 명령어들을 순서대로 입력하여 db 생성

---- frontend part ----
1. In flontend(main) directory -> yarn install
2. In frontend(main) directory -> .env.local 파일 -> NEXT_PUBLIC_SERVER_URL=http://localhost:8000/ 에서 localhost 부분을 web application server ip로 변경(web application server와 web을 동일한 pc에서 구동할 경우 localhost로 둬도 무방)

---- 구동 part ----
1. Web application server 구동 -> cloudmanager(main) directory에서 python manage.py runserver 0.0.0.0:8000 --noreload 명령어 실행
2. Web 구동 -> frontend(main)에서 yarn dev 명령어 실행
3. URL에 http://localhost:3000/auth/sigin 을 입력하여 로그인 페이지로 이동, 회원가입 및 로그인을 통해 시스템 사용 가능
