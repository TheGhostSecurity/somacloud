# SomaCloud: Copy-ready technical report content

**How to use this file.** Paste the sections below under the matching headings in your report. Text in `[square brackets]` must be replaced with your own personal, institutional, or research information. Do not invent questionnaire results, screenshots, or test outcomes. The content reflects the implementation in this repository as at 6 August 2026.

## Preliminary pages

### Title page

**DESIGN AND IMPLEMENTATION OF A WEB-BASED CYBERSECURITY SANDBOX ENVIRONMENT (SOMACLOUD) AT THE DAR ES SALAAM INSTITUTE OF TECHNOLOGY**

A project report submitted in partial fulfilment of the requirements for the award of Bachelor of Engineering in Computer Engineering at the Dar es Salaam Institute of Technology.

By

**KATIMBA, BURHANI H**  
Registration Number: **220242443851**

Supervisor: **Mr. Alfred Kajirunga**  
[Month, Year]

### Declaration

I, Katimba Burhani H, declare that this project report titled *Design and Implementation of a Web-Based Cybersecurity Sandbox Environment (SomaCloud) at the Dar es Salaam Institute of Technology* is my original work and has not been submitted to any other institution for the award of a degree or any other academic qualification. All sources used have been acknowledged.

Candidate signature: ____________________ Date: ____________________

### Certification

This is to certify that this project report titled *Design and Implementation of a Web-Based Cybersecurity Sandbox Environment (SomaCloud) at the Dar es Salaam Institute of Technology* was carried out by Katimba Burhani H under my supervision and is submitted with my approval.

Supervisor signature: ____________________ Date: ____________________

### Dedication

This work is dedicated to my family, lecturers, and all students whose interest in practical cybersecurity learning inspired the development of an accessible and safe learning platform.

### Abstract

Practical cybersecurity education requires learners to use security tools and realistic targets in a controlled environment. However, many students cannot run multiple virtual machines and specialised tools on their personal computers because of limited processor capacity, memory, storage, or financial resources. This project designed and implemented SomaCloud, a web-based cybersecurity sandbox environment for the Dar es Salaam Institute of Technology (DIT). SomaCloud centralises practical laboratories on managed Docker worker nodes and makes them available through a browser-based interface.

The system was implemented using Python, Django, HTML templates, SQLite for local development with PostgreSQL support for production, Docker Remote API, Transport Layer Security (TLS), and container images. It supports student, instructor, and administrator roles; laboratory creation and publication; enrolment; guided theory; isolated terminal and target-service containers; flag- or question-based challenges; progress tracking; node health checks; session time limits; resource profiles; and student analytics. For every launched laboratory, the orchestration component selects an active node with sufficient CPU, memory, and port capacity, reserves ports transactionally, creates a unique Docker bridge network, applies CPU and memory limits, and removes containers, networks, and port reservations when the session is stopped or expires.

The project used an Agile methodology and questionnaire-based requirements collection. The implemented design addresses the identified accessibility, hardware-dependency, institutional-customisation, monitoring, and resource-management gaps. SomaCloud provides a foundation for safe hands-on learning while ensuring that vulnerable practice services are separated from each other and from the application through per-session container networks. Future work includes production hardening, a PostgreSQL deployment, expanded laboratory content, load testing, and correcting legacy automated tests that no longer match the current routes.

### List of abbreviations

| Abbreviation | Meaning |
|---|---|
| API | Application Programming Interface |
| CPU | Central Processing Unit |
| DFD | Data Flow Diagram |
| DIT | Dar es Salaam Institute of Technology |
| ERD | Entity Relationship Diagram |
| HTTP/HTTPS | Hypertext Transfer Protocol / Secure HTTP |
| RAM | Random Access Memory |
| RBAC | Role-Based Access Control |
| SDLC | Software Development Life Cycle |
| SRS | Software Requirements Specification |
| TLS | Transport Layer Security |
| UML | Unified Modeling Language |

## CHAPTER ONE: INTRODUCTION

### 1.1 Background of the Study

Cybersecurity is a practical discipline. Learners need to use tools such as network scanners, web-testing tools, password-auditing tools, and forensic utilities against authorised targets in order to understand how systems are attacked and defended. Conventional lectures alone cannot provide this experience. Local virtual-machine laboratories can provide practical training, but they require relatively high CPU, RAM, storage, and configuration skills from every student.

SomaCloud was developed as an institutional web platform that moves the intensive laboratory workload from a student's personal device to centrally managed Docker nodes. A student uses a standard web browser to enrol in a lab, read learning material, launch an isolated browser terminal, interact with deliberately vulnerable target services, submit a flag or answer, and view progress. Instructors create and manage labs, configure resource profiles, monitor sessions, and view learner analytics. Administrators manage users, Docker nodes, SSH setup keys, and system operation.

The platform uses containers instead of requiring a full virtual machine for every learner. Each practical session receives a private Docker bridge network, a terminal container, zero or more service containers, reserved host ports, a resource limit, and an expiry time. This enables repeatable and disposable training environments and reduces the chance that one learner's experiment interferes with another learner's environment.

### 1.2 Problem Statement

DIT students need hands-on cybersecurity practice, but many have devices that cannot reliably run multiple virtual machines and security tools. Commercial online laboratories can also be costly, have limited free tiers, or cannot be adapted to a specific course. Local laboratories are difficult to configure consistently and create a risk when vulnerable software or attack exercises are run outside a controlled environment. In addition, an institution needs a way to manage learning resources, monitor student progress, control session duration, and allocate limited server CPU and RAM fairly.

Therefore, there is a need for an institution-hosted, browser-accessible system that provisions isolated cybersecurity laboratories, applies resource limits, records learning progress, and gives instructors and administrators visibility of usage and performance.

### 1.3 Aim of the Project

To design and implement a secure, web-based cybersecurity sandbox environment that provides DIT students with centrally hosted, isolated, and manageable practical cybersecurity laboratories.

### 1.4 Specific Objectives

1. To implement user registration, authentication, profile management, and role-based access for students, instructors, and administrators.
2. To implement browser-accessible, Docker-based cybersecurity laboratory sessions containing a terminal and optional vulnerable target services.
3. To implement laboratory enrolment, theory, challenge submission, completion tracking, session monitoring, and student analytics.
4. To implement resource profiles, node selection, CPU and memory limits, port reservation, time-limited sessions, health checking, and cleanup of sandbox resources.

### 1.6 Scope of the Project

The project covers a Django web application named SomaCloud. Its scope includes user accounts, role permissions, laboratory authoring, learning content, lab enrolment, Docker container orchestration, isolated networks, challenge evaluation, progress records, analytics, resource profiles, Docker-node administration, SSH-key handling, and TLS-authenticated communication with Docker APIs. The system can use SQLite during local development and is configured to use PostgreSQL in production.

The project does not implement a machine-learning prediction model, automatic grading of arbitrary terminal commands, a public multi-tenant cloud service, payment integration, password-reset email delivery, or complete production observability and backup automation. A separate Docker host and correctly configured certificates are required to launch real labs.

### 1.7 Significance of the Project

SomaCloud reduces the dependence on powerful student computers because containers run on institution-managed nodes. It supports more consistent practical exercises because an instructor selects approved container images and resource profiles. Isolation, disposable networks, session expiry, and automated cleanup reduce operational risk. Progress and activity records give students feedback and give instructors evidence for monitoring engagement. Finally, the multi-node design allows the institution to expand capacity by registering additional Docker workers rather than redesigning the application.

### 1.8 Limitations

The platform's capacity depends on available Docker-node CPU, RAM, network bandwidth, port ranges, and image-download speed. A lab currently requires a browser-terminal container; if no terminal image or no eligible active node is available, deployment fails. The local settings file has `DEBUG=True` and a development secret key, therefore it must not be treated as a production-secure configuration. The design requests TLS for Docker API calls, but the current local certificate path is incomplete; Docker health checks in this environment cannot authenticate until valid certificates are installed. Some legacy tests refer to removed learning-path routes and must be revised. These are implementation limitations, not evidence that the architectural approach is invalid.

## CHAPTER TWO: LITERATURE REVIEW

### 2.4 Existing Systems Review

Existing cybersecurity training approaches generally fall into three groups: subscription cloud platforms, local virtual-machine laboratories, and institution-hosted cyber ranges. Subscription platforms are convenient but may impose recurring cost, limited free access, and restricted institutional customisation. Local virtual machines give learners control but transfer CPU, RAM, storage, setup, and maintenance requirements to each student. Institutional cyber ranges offer control over curriculum and data, but require infrastructure management and should integrate learning, monitoring, and resource allocation rather than only providing machines.

**Weaknesses addressed by SomaCloud:**

| Existing approach | Main weakness | SomaCloud response |
|---|---|---|
| Commercial cloud lab | Cost and limited curriculum customisation | Institution-owned labs, images, phases, theory, hints, and challenges |
| Student-owned virtual machines | High hardware requirement and inconsistent setup | Central Docker execution accessed through a browser |
| Stand-alone local lab | Difficult supervision and weak progress evidence | Enrolment, progress stages, submissions, login/page-view logs, and instructor analytics |
| Single-server lab | Limited capacity and difficult resource control | Docker-node registry, capacity-aware node selection, resource profiles, and port reservations |

### 2.5 Project Research Gap

The gap is an institution-tailored platform that combines safe browser-based cybersecurity practice with curriculum management, learner progress tracking, analytics, and resource-aware container orchestration. SomaCloud addresses this through per-session Docker networks, controlled image selection, role-based workflows, progress records, node capacity checks, and automated expiry cleanup.

### 2.6 Proposed System

SomaCloud is a three-tier web platform. The presentation layer provides dashboards and lab pages in a web browser. The Django application layer authenticates users, enforces role permissions, manages learning records, and orchestrates container sessions through the Docker Remote API. The data layer stores users, roles, labs, content, resource profiles, sessions, progress, submissions, nodes, port reservations, and logs. Docker worker nodes execute the terminal and target-service containers.

### 2.7 Conceptual Framework

Use this as the proposed-system architecture figure. Redraw it in draw.io, Visio, or Word using boxes and arrows.

```text
Students / Instructors / Administrators
                 |
                 v
      Web browser and Django templates
                 |
                 v
       Django application (SomaCloud)
  Authentication | Labs | Progress | Analytics
  Node management | Sandbox orchestrator
                 |
        TLS-authenticated Docker API
                 |
                 v
       Active Docker worker node selected
                 |
   +-------------+-------------+
   | Per-session Docker bridge |
   +-------------+-------------+
       |                       |
       v                       v
 Browser terminal        Vulnerable target service(s)
 (ttyd container)        (web/SQLi/XSS/IDOR/CMDi/LFI)
                 |
                 v
 Database: users, labs, sessions, progress, logs
```

### 2.8 Strengths of the Proposed System

The proposed system centralises resource-intensive work, supports role separation, uses vetted container images, applies CPU and memory limits, keeps each session in a unique network, records learning progress, releases resources automatically, and can add worker nodes. It also gives instructors tools to manage labs and view analytics while allowing students to work from ordinary browsers.

## CHAPTER THREE: PROJECT RESEARCH METHODOLOGY

### 3.1 Introduction

This project used a design-and-development research approach. Requirements were collected from intended users, analysed using descriptive statistics, converted into functional and non-functional requirements, and implemented incrementally as a working web system.

### 3.2 Research Design

The study used a mixed-method, descriptive design. Closed questionnaire questions produced numerical data such as frequencies and percentages. Open questions, interviews, observations, and document review can provide explanations of the challenges students face when conducting practical cybersecurity work. The system-development part of the study used an iterative Agile approach.

### 3.3 Study Area

The study area was the Dar es Salaam Institute of Technology (DIT), focusing on students in computing-related programmes, cybersecurity instructors, and ICT support personnel who interact with practical laboratory infrastructure.

### 3.4 Target Population and their Categories

The target population consisted of: (i) students taking computing or cybersecurity-related courses, (ii) instructors responsible for cybersecurity teaching and assessment, and (iii) ICT support staff responsible for infrastructure, networking, servers, or laboratory support.

### 3.6 Sample Size

The completed document reports **25 DIT student respondents**. State the final number of instructors and ICT staff only if they actually participated. Do not claim that all three groups completed questionnaires unless the raw responses prove it.

### 3.7 Data Collection Methods

**Questionnaires.** Structured questionnaires collected evidence about students' hardware limitations, access to practical cybersecurity labs, required features, progress tracking, and automated resource management.

**Interviews.** Semi-structured interviews with instructors or ICT personnel may be used to validate operational requirements such as lab approval, session limits, monitoring, server management, and safety controls. Include this only if interviews were actually carried out.

**Observation.** Observe a student attempting to run security tools or virtual machines locally and record bottlenecks such as insufficient RAM, slow startup, configuration errors, and lack of a safe target environment.

**Document Review.** Review course practical requirements, existing lab procedures, Docker documentation, Django documentation, and the current SomaCloud implementation to identify required functions and technical constraints.

### 3.8 Data Collection Instruments

The principal instrument was a structured questionnaire with closed questions and optional open comments. An interview guide, observation checklist, and document-review checklist should be included in the appendices only when used. The questionnaire should identify respondent category, device capability, prior practical-lab experience, desired platform features, and perceived usefulness of progress and resource management.

### 3.9 Data Required for Each Objective

| Objective | Required data | Implementation evidence |
|---|---|---|
| User management | Need for separate roles, accounts, and permissions | Django authentication; Student, Instructor, and Administrator workflows |
| Sandbox environment | Device limitations; need for browser labs and isolation | Docker containers, unique bridge networks, browser terminal |
| Progress and monitoring | Need to track completion and performance | LabProgress, Progress, FlagSubmission, LoginLog, PageViewLog, analytics views |
| Resource management | Expected resource limits, session duration, availability | ResourceProfile, DockerNode, PortReservation, CPU/RAM limits, expiry cleanup |

### 3.10 Ethical Considerations

Respondents should participate voluntarily and be informed of the project purpose. Questionnaire data should be anonymised in the report, stored securely, and used only for academic purposes. The sandbox must be used only for authorised exercises. Vulnerable containers must be isolated and should not be used to attack external systems. Administrative access, SSH private keys, Docker TLS certificates, and user credentials must be protected and never included in screenshots or appendices.

### 3.11 Data Analysis Methods

Questionnaire data was analysed with descriptive statistics: frequency and percentage. The formula used was:

`Percentage = (frequency / total respondents) × 100`

Open-ended responses should be coded into themes, for example hardware limitations, need for browser access, desired progress feedback, and server-resource concerns. The existing report identifies 52% reporting hardware difficulty, 80% supporting progress tracking, and 88% supporting automated resource management. Retain these percentages only if they agree with the questionnaire results in Appendix B.

### 3.12 Development Methodology

Agile development was used because the platform contains independent but related modules that can be delivered and evaluated in increments. The iterations were: (1) requirements and role design; (2) authentication and dashboards; (3) lab and learning-content management; (4) container orchestration and resource controls; (5) progress, analytics, and reporting; and (6) testing and refinement. Each increment was reviewed before adding the next function.

### 3.13 Software and Hardware Used

| Category | Technology / specification |
|---|---|
| Backend | Python and Django 6.0.6 |
| Front end | Django HTML templates, CSS, JavaScript in templates |
| Local database | SQLite (`db.sqlite3`) |
| Production database support | PostgreSQL through `psycopg2-binary 2.9.10` |
| Container platform | Docker Engine and Docker Remote API |
| Docker communication | Python `requests 2.32.3` with TLS client certificate, key, and CA verification |
| Remote node setup | Paramiko 5.0.0 / SSH |
| Image and reporting support | Pillow 12.2.0, Matplotlib 3.10.7, ReportLab 4.4.0, pypdf 5.1.0 |
| Application server requirement | A server running Django with network access to Docker worker nodes |
| Worker-node requirement | Docker Engine, configured port range, CPU/RAM capacity, and valid TLS credentials |
| Client requirement | Modern web browser and Internet/institutional network access |

## CHAPTER FOUR: DATA ANALYSIS

### 4.1 Introduction

This chapter presents the analysis of requirements data collected from intended users. The analysis is organised according to the project objectives and connects each identified need to an implemented SomaCloud feature.

### 4.2 Respondent Demographics

Insert a table using only your actual questionnaire data:

| Characteristic | Category | Frequency | Percentage |
|---|---|---:|---:|
| Respondent role | Student / Instructor / ICT staff | [ ] | [ ] |
| Programme or department | [actual categories] | [ ] | [ ] |
| Year of study | [actual categories] | [ ] | [ ] |
| Prior cybersecurity practical experience | Yes / No | [ ] | [ ] |

### 4.3 Analysis of Collected Data

**Hardware and laboratory access.** The reported finding that 52% of the 25 respondents experienced difficulty completing cybersecurity practical work because of hardware limitations supports centralising compute resources. In SomaCloud, CPU and memory are supplied by a Docker worker node instead of the student's device. The student's device only requires browser access.

**User management.** Respondents supported separate accounts and responsibilities. SomaCloud implements user registration, secure Django password hashing, authentication, user profiles, and role separation. Students enrol and conduct labs; instructors create, edit, publish, monitor, and delete their own labs; administrators manage users and platform infrastructure.

**Progress monitoring.** The reported 80% support for progress tracking justifies the `LabProgress`, `Progress`, `FlagSubmission`, `LoginLog`, and `PageViewLog` records. The platform records theory, sandbox, challenge, and complete stages, timestamps completion, displays progress, and supplies instructor/student analytics and PDF reporting functions.

**Resource management.** The reported 88% support for automated resource management justifies resource profiles and the orchestration logic. A profile specifies CPU cores, RAM in MB, and a session time limit. The scheduler chooses an active node only if it has free ports and sufficient CPU and memory. Expired sessions are stopped and their containers, networks, and ports are released.

### 4.4 Interpretation of Findings

The findings show that accessibility is not only a content problem; it is also an infrastructure problem. Centralised containers address hardware constraints, while role-based management and progress tracking address supervision. The demand for automated resource management is reflected in the platform's resource profiles, port reservations, node-capacity checks, and session expiry mechanism. The data therefore supports the four project objectives.

### 4.5 Identified Problems

1. Students may lack the CPU and RAM needed to run virtual machines and security tools locally.
2. Existing external platforms may be costly, generic, or restricted.
3. Local labs can be inconsistently configured and difficult to supervise.
4. Vulnerable exercises can create risk when they are not isolated.
5. Instructors need a reliable record of enrolment, activity, completion, and submissions.
6. A finite server infrastructure needs fair resource allocation and automatic cleanup.

### 4.6 Functional Requirements Identified

The system shall support registration and login; student, instructor, and administrator roles; profile management; lab creation and publication; lab enrolment; theory delivery; browser-accessible terminal sessions; optional vulnerable target services; flag or question challenges; progress recording; analytics; node configuration; health checks; SSH key registration; resource profiles; port reservation; session stop; and expiry cleanup.

### 4.7 Non-functional Requirements Identified

The platform shall protect access through authentication, authorisation, CSRF middleware, password hashing, TLS for Docker API calls, and least-privilege administration. It shall limit each container's CPU and RAM, isolate session networks, avoid port conflicts, and release resources after stop or expiry. It should be usable through a standard browser and should be scalable by adding Docker nodes. Production deployment should use `DEBUG=False`, an environment-supplied secret key, HTTPS, PostgreSQL, backups, monitoring, and valid certificate management.

### 4.8 Summary

The requirements analysis supports a browser-accessible, centrally hosted cybersecurity sandbox. The final requirements directly informed the resource manager, sandbox orchestrator, user workflows, and monitoring functions implemented in SomaCloud.

## CHAPTER FIVE: SYSTEM REQUIREMENT SPECIFICATION

### 5.2 Existing System Analysis

Before SomaCloud, a student would typically use a personal computer or a third-party platform. The student installs tools and virtual machines, configures targets, consumes local resources, and has limited institution-specific monitoring. In the proposed system, the student interacts with a browser, while a managed server runs isolated containers and stores progress centrally.

### 5.3 Proposed System

The proposed system is a Django application connected to Docker worker nodes. An instructor defines a lab, attaches a browser-terminal image and optional target-service images, chooses a resource profile, and publishes it. A student enrols and launches it. The orchestrator verifies capacity, reserves ports, pulls images when required, creates a unique network, starts target services and the terminal, saves endpoints and URLs, and marks the session running. When a session is stopped, expires, or fails, the system performs cleanup.

### 5.4 Functional Requirements

| ID | Requirement |
|---|---|
| FR-01 | The system shall allow a student to create an account and log in using Django authentication. |
| FR-02 | The system shall distinguish Student, Instructor, and Administrator roles. |
| FR-03 | The system shall allow instructors to create, edit, publish, toggle, and delete authorised labs. |
| FR-04 | The system shall allow students to view published labs and enrol once per lab. |
| FR-05 | The system shall display lab theory, notes, tools, and challenge information. |
| FR-06 | The system shall launch one active sandbox per student per lab. |
| FR-07 | The system shall create a private Docker bridge network for each sandbox session. |
| FR-08 | The system shall start one terminal container and zero or more service containers for a lab. |
| FR-09 | The system shall apply a resource profile containing CPU, RAM, and a time limit. |
| FR-10 | The system shall reserve available host ports before starting containers. |
| FR-11 | The system shall record terminal URLs, service endpoints, status, start time, expiry time, and assigned node. |
| FR-12 | The system shall allow students to submit a flag or answer and record each submission. |
| FR-13 | The system shall mark theory, sandbox, challenge, and completion stages. |
| FR-14 | The system shall provide student and instructor analytics, including recent activity and PDF export. |
| FR-15 | The system shall allow administrators to register, configure, health-check, verify, enable, drain, and remove Docker nodes. |
| FR-16 | The system shall stop expired sessions and release their containers, networks, and port reservations. |

### 5.5 Non-functional Requirements

**Security:** authentication, password validation/hashing supplied by Django, role checks, CSRF middleware, Docker TLS verification, restricted SSH key file permissions (`0600`), per-session networks, and audited login/page-view records.

**Performance:** a node is selected only when it has enough port, CPU, and memory capacity. Container limits use Docker `NanoCpus`, `Memory`, and `MemorySwap` settings.

**Reliability:** transactional port reservation prevents duplicate reservations; failure handling removes created containers, networks, and reservations; node verification conducts ping, image pull, container-create/start, and cleanup checks.

**Maintainability:** modules separate models, views, forms, services, orchestration, templates, migrations, and management commands. Content can be synchronised from the `content/` directory.

**Availability and scalability:** active nodes are selected dynamically and new workers can be registered. Availability remains limited by server capacity and correct TLS/Docker configuration.

**Usability:** responsive web templates provide dashboards, lab lists, forms, session pages, status checks, and progress displays; students use a browser rather than local virtualisation.

### 5.6 User Requirements

| User | Main requirements |
|---|---|
| Student | Sign up, log in, update profile, browse/enrol in labs, read theory, launch/stop lab, submit challenge, view progress and analytics. |
| Instructor | Create and manage labs, define images and resource profiles, monitor live sessions, review student analytics, and manage course resources. |
| Administrator | Manage users and roles, nodes, SSH keys, health/verification operations, resource capacity, and platform status. |

### 5.7 System Requirements

**Hardware:** application server; one or more Docker worker nodes; adequate CPU/RAM based on simultaneous resource profiles; reliable networking; and client devices capable of running modern browsers.

**Software:** Python 3, Django 6.0.6, Docker Engine, SQLite for development or PostgreSQL in production, requests, Paramiko, valid TLS certificates, and a Linux-compatible deployment environment.

**Network:** the app server must reach Docker Remote API endpoints (normally TCP 2376 secured with TLS); students must reach the web application and published browser-terminal ports; workers need image-registry access where images are not already available.

**Machine learning and algorithms:** no machine-learning model is implemented. The operational scheduling algorithm is a capacity-aware best-fit heuristic: it rejects non-active, port-full, CPU-insufficient, and memory-insufficient nodes, then selects the eligible node with the greatest normalised remaining CPU and memory headroom. If no session profile is supplied, it uses remaining port capacity.

### 5.8 Feasibility Study

**Technical feasibility:** Django, Docker, TLS, SSH, SQLite/PostgreSQL, and browser interfaces are established technologies. The repository contains the implemented modules. Correct certificates and reachable Docker nodes remain prerequisites.

**Economic feasibility:** open-source Python, Django, Docker, SQLite, PostgreSQL, and Linux reduce software licence costs. The major cost is server/cloud CPU, RAM, bandwidth, storage, and maintenance.

**Operational feasibility:** students use familiar browser workflows; instructors use forms and dashboards; administrators require Docker and certificate-management skills.

**Legal and ethical feasibility:** only authorised learning exercises and deliberately vulnerable containers should be used. The institution must protect personal data and credentials, establish acceptable-use rules, and prevent the platform being used against external targets.

**Schedule feasibility:** Agile iterations allow the system to be delivered and tested module by module. Production hardening and expanded content can be planned as later iterations.

### 5.9 Software Requirement Specification: Use-case content

**Actors:** Student, Instructor, Administrator, Docker Worker Node.

**Student use cases:** register; log in; manage profile; browse labs; enrol; read theory; launch sandbox; access terminal; stop sandbox; submit flag/answer; view progress and analytics.

**Instructor use cases:** log in; create/edit/publish lab; choose image and resource profile; monitor sessions; manage resource profiles; view student analytics; export report.

**Administrator use cases:** manage users; assign role; register/manage Docker nodes; upload/remove SSH keys; initiate health check; verify a node; monitor platform.

**Docker Worker Node use cases:** accept authenticated API request; pull approved image; create network; run limited containers; return status; stop and remove resources.

## CHAPTER SIX: SYSTEM DESIGN

### 6.2 System Architecture

SomaCloud uses a three-tier architecture: presentation (Django templates in the browser), application (Django views, forms, services, and orchestrator), and data (Django ORM with SQLite locally or PostgreSQL in production). Docker nodes are an execution tier attached to the application through a TLS-protected Docker Remote API. This separation means user-interface changes, database changes, and container-execution changes can be maintained independently.

### 6.3 Data Modeling: Context Diagram

```text
[Student] ---> registration, enrolment, launch, answer ---> [SomaCloud]
[Student] <--- lab content, terminal URL, progress -------- [SomaCloud]
[Instructor] ---> lab/resource updates, monitoring -------> [SomaCloud]
[Instructor] <--- sessions, analytics, reports ------------ [SomaCloud]
[Administrator] ---> users/nodes/keys/health actions -----> [SomaCloud]
[Administrator] <--- platform and capacity information ---- [SomaCloud]
[SomaCloud] <---- Docker status / container details ------> [Docker Node]
[SomaCloud] <---------------- persistent records ---------> [Database]
```

### Data Flow Diagram: Level 0 and Level 1

**Level 0:** The external entities are Student, Instructor, Administrator, and Docker Node. The central process is SomaCloud. The data stores are the application database and Docker images/containers on the worker.

**Level 1 processes:** (1.0) Authentication and role control; (2.0) laboratory and content management; (3.0) sandbox orchestration; (4.0) progress, submissions, and analytics; (5.0) node/resource administration. Process 3.0 reads the lab resource profile, selects a node, creates a session, reserves ports, creates the network/containers, and writes the session state. Process 4.0 writes completion and submission records and reads them for dashboards/reports.

### 6.4.1 Database Design

**Core tables / entities**

| Entity | Purpose | Important relationships |
|---|---|---|
| User | Django authentication user | One student/instructor profile; creates labs; owns enrolments, sessions, submissions, logs |
| StudentProfile / InstructorProfile | Optional role-specific profile data | One-to-one with User |
| HackPhase | Ordered cybersecurity phase | One-to-many Labs |
| Lab | A practical cybersecurity exercise | Belongs to phase, instructor, resource profile; has images, tools, enrolments, sessions |
| ContainerImage | Approved terminal or service Docker image | Used by Labs |
| ResourceProfile | CPU, RAM, session-time limit | Used by Labs and Activities |
| LabEnrollment | Student's active lab enrolment | Unique per User and Lab |
| LabProgress | Completion by stage | Unique per User, Lab, and stage |
| SandboxSession | A deployed environment | Belongs to User, Lab, and optional DockerNode |
| PortReservation | Reserved host port | Unique port; belongs to one session |
| FlagSubmission | Submitted flag/answer and correctness | Belongs to User and Lab |
| DockerNode | Docker worker configuration and capacity | Has sessions and optional SSH key |
| SSHKey | Private key used during node setup | May be linked to a DockerNode |
| LearningPath, Module, Activity, ActivityStage, Assessment | File/database-backed learning content | Hierarchical learning content and progress |
| LoginLog / PageViewLog | Authentication and engagement audit data | Belongs to User where applicable |

**Important database constraints:** unique enrolment per user/lab; unique progress record per user/lab/stage; unique port reservation; unique lab slug within a phase; unique module slug within a learning path; unique activity slug within a module; and unique activity stage type/order within an activity.

### 6.5 Process Modeling

#### Use-case descriptions

**Launch sandbox.** Preconditions: authenticated student, active enrolment, lab has terminal image, active node has capacity. Main flow: create pending session; select node; ensure images; reserve ports; create network; start service containers; start terminal container; save URLs/endpoints; mark session running. Alternative flow: if any step fails, remove created resources, release ports, set session to error, and show an error message.

**Submit challenge.** Preconditions: authenticated/enrolled student and lab challenge configured. Main flow: receive flag/answer; compare it with configured correct value; store submission; if correct, mark challenge and complete stages; stop active sandbox; display result. Alternative flow: store incorrect submission and display configured hint.

#### Activity diagram: sandbox launch

```text
Start -> Student requests launch -> Existing active session?
  Yes -> Open existing session -> End
  No -> Create pending session -> Select eligible node
    No node -> Set ERROR -> Notify student -> End
    Node found -> Pull/check images -> Reserve ports -> Create network
      Failure -> Cleanup -> Set ERROR -> End
      Success -> Start targets -> Start terminal -> Save endpoints/URL
                -> Set RUNNING -> Display sandbox -> End
```

#### Sequence diagram: sandbox launch

```text
Student -> Django view: launch lab
Django view -> Database: create pending SandboxSession
Django view -> Orchestrator: deploy_sandbox(session)
Orchestrator -> Database: choose node / reserve ports
Orchestrator -> Docker node: pull images, create network, create/start containers
Docker node --> Orchestrator: container IDs and IP addresses
Orchestrator -> Database: save running session and terminal URL
Django view --> Student: redirect to sandbox page
```

#### Class diagram content

User has StudentProfile or InstructorProfile. User has many LabEnrollment, LabProgress, SandboxSession, FlagSubmission, LoginLog, PageViewLog, Enrollment, and Progress records. Instructor User creates many Lab records. Lab belongs to HackPhase and ResourceProfile, has one terminal ContainerImage and many service ContainerImage objects, and has many SandboxSession records. SandboxSession belongs to one Lab, one User, and optionally one DockerNode; it has many PortReservation records. LearningPath contains Modules, Modules contain Activities, and Activities contain ActivityStages and optionally one Assessment.

#### Deployment diagram content

```text
Client browser
     |
     | HTTP/HTTPS
     v
Django application server
  - templates, views, ORM, orchestrator
  - SQLite development / PostgreSQL production
     |
     | Docker Remote API over TLS
     v
Docker worker node(s)
  - Docker Engine
  - per-session bridge networks
  - ttyd terminal containers
  - vulnerable service containers
```

### 6.7 User Interface Design

Include screenshots, with captions, of: home/login; student dashboard; lab catalogue; lab detail showing theory and challenge; active sandbox with terminal; student analytics/profile; instructor dashboard/lab form/live monitor; administrator control panel; Docker-node list/detail; resource-profile form. Remove real IP addresses, private keys, passwords, certificate paths, tokens, flags, and personally identifiable respondent data from screenshots.

### 6.8 Hardware or Automation Design

The resource manager automates provisioning and cleanup. A ResourceProfile contains CPU count, memory in MB, and time limit. When a lab starts, the system calculates resource use from all running sessions on each node. It excludes nodes that are inactive, lack two available ports per possible sandbox capacity, or do not have sufficient CPU/RAM. It uses the eligible node with the greatest remaining normalised headroom. Docker is instructed to apply memory, memory-swap, and NanoCPU limits. A management command and page-level checks stop sessions whose expiry time has passed.

### 6.9 Machine Learning and Dataset Design

Not applicable to the implemented version. SomaCloud collects operational logs that could support future research (login times, page views, duration, lab progress, submissions, session status, and resource use), but no ML model, training dataset, feature-engineering process, or prediction output is currently implemented. Do not describe an ML algorithm as implemented.

### 6.9 Algorithms of the Working System

**Node-selection algorithm (pseudocode):**

```text
neededCPU, neededRAM <- session.lab.resourceProfile
bestNode <- null; bestScore <- -1
for each node where status = ACTIVE:
    if currentSessions >= portCapacity: continue
    usedCPU, usedRAM <- sum resources of RUNNING sessions on node
    availableCPU <- totalCPU - usedCPU
    availableRAM <- totalRAM - usedRAM
    if neededCPU > availableCPU or neededRAM > availableRAM: continue
    score <- remainingCPU/totalCPU + remainingRAM/totalRAM
    if score > bestScore: bestNode <- node; bestScore <- score
return bestNode
```

**Session cleanup algorithm:** stop terminal and service containers; remove the session network; delete port reservations; set status to STOPPED or EXPIRED; record stop time; decrement node session count without allowing it to fall below zero.

### 6.10 Flowchart of the Working System

```text
Login -> Role dashboard -> Student selects lab -> Enrolment verified
 -> Launch request -> Resource/node check -> Isolated containers started
 -> Student performs exercise -> Flag/answer submitted
 -> Correct? --No--> Show hint and continue
              --Yes--> Record completion -> Stop session -> Update analytics
```

### 6.11 Security Design

Security controls include Django authentication and password validation; role checks in views; CSRF middleware; clickjacking middleware; TLS client authentication for Docker API calls; isolated bridge networks; resource limits; random network/container names; port reservations; time-based cleanup; SSH private-key permission `0600`; and activity/login/page-view records. Recommended production improvements are HTTPS for end users, environment variables for all secrets, `DEBUG=False`, a restricted `ALLOWED_HOSTS` list, database backups, a firewall that limits Docker API access to the application server, Docker daemon hardening, container image scanning, and centralised audit logging.

## CHAPTER SEVEN: SYSTEM IMPLEMENTATION, TESTING AND RESULTS

### 7.1 Introduction

This chapter describes the implementation of SomaCloud, the tools used, the implemented modules, and the results of verification. The system is a working Django application with Docker-based sandbox orchestration; however, the report must distinguish implementation evidence from tests that are still incomplete.

### 7.2 Development Environment

The project source is organised into a Django project (`sandbox`) and an application module (`core`). Key implementation files are `core/models.py` for persistent entities, `core/views.py` for user workflows, `core/forms.py` for input validation, `core/orchestrator.py` for Docker operations, `core/services.py` for progress/dashboard calculations, `core/middleware.py` for page-view logging, `core/management/commands/` for operational commands, and `templates/` for the interface. Content can be represented in the `content/` directory and synchronised into the database.

### 7.3 Software Tools Used

Python, Django 6.0.6, SQLite, PostgreSQL driver, Docker Engine, Docker Remote API, requests, Paramiko/SSH, HTML/CSS/JavaScript templates, Matplotlib, ReportLab, Pillow, and Git were used. Docker images include a browser-terminal image based on `ttyd` and intentionally vulnerable service images such as SQL injection, cross-site scripting, insecure direct object reference, command injection, local file inclusion, and upload practice labs.

### 7.4 Implementation of Modules

**User management module.** Implements sign-up, login/logout, Django password validation, profile changes, student profile images, and administrator-managed user roles. Instructors are represented through the `Instructor` group; administrators use Django staff/superuser flags.

**Laboratory management module.** Implements hack phases, tools, container images, labs, theory content, notes, challenge types, hints, publication state, and resource profiles. The lab form accepts terminal and service image tags and creates registered container-image records when needed.

**Sandbox module.** Creates a `SandboxSession`, selects a node, pulls images, reserves ports atomically, creates a unique network named `somacloud-<random-id>`, starts services before the terminal, injects service endpoint information into terminal environment variables, builds the terminal URL, and saves state.

**Progress and analytics module.** Tracks theory, sandbox, challenge, and complete stages. It records flag/question submissions, logs login/page-view events, supports student analytics, instructor analytics, charts, and PDF report generation.

**Resource and node-management module.** Stores worker addresses, port ranges, status, capacity, SSH information, health time, and setup tokens. It can detect Docker CPU/RAM data through `/info`, run a node smoke test, and stop expired sessions.

### 7.5 Testing Strategy

Use four levels of testing:

1. **Unit testing:** test forms, models, role checks, progress calculations, node-selection decisions, port reservation, and session status logic.
2. **Integration testing:** test Django views with the database; test Docker API interactions using a non-production worker; test complete launch/stop/expiry workflows.
3. **System testing:** test each role through a browser, including lab authoring, enrolment, launching, submission, analytics, node operations, and error messages.
4. **User acceptance testing:** ask selected students/instructors to complete a realistic lab and rate accessibility, clarity, and usefulness.

### 7.6 Test Cases

| ID | Test case | Expected result | Current status/evidence |
|---|---|---|---|
| TC-01 | Student signs up with valid data | Account created; student role assigned | Implemented; automated test passes |
| TC-02 | Admin creates instructor | Account is added to Instructor group | Implemented; automated test passes |
| TC-03 | Student tries to access admin panel | Redirected/denied | Implemented; automated test passes |
| TC-04 | Student enrols in a published lab | One active enrolment created | Implemented; manual/integration evidence required |
| TC-05 | Student launches an already active lab | Existing session is reused; duplicate is prevented | Implemented in view logic; manual/integration evidence required |
| TC-06 | Eligible node is selected | Node has active state, ports, CPU, and RAM | Implemented; add targeted unit test |
| TC-07 | Sandbox launch succeeds | Network, containers, URLs, endpoints, and RUNNING status saved | Requires valid TLS Docker worker test |
| TC-08 | Sandbox launch fails midway | Containers/network/ports cleaned; status ERROR | Implemented; add mocked Docker integration test |
| TC-09 | Correct flag/answer submitted | Submission stored; challenge and completion marked; active session stopped | Implemented; manual/integration evidence required |
| TC-10 | Session expiry | Containers/network/ports removed; status EXPIRED | Implemented; test with controlled expiry time |
| TC-11 | Node verification | Ping, pull, create, start, cleanup all pass | Requires configured TLS certificates and worker |

### 7.7 Results

The codebase contains the implemented user, laboratory, resource, orchestration, progress, analytics, node-administration, and logging modules described above. A local automated-test run found 13 tests. Eight passed. Five did not pass: four legacy learning-engine tests refer to route names (`learning_paths`, `activity_detail`, `complete_activity_stage`) that are not present in the current URL configuration, and one test expects an administrator dashboard redirect to `/admin/` while the current implementation redirects to `/instructor-dashboard/`. The Django system check reported no issues. Docker health calls in the current local environment cannot complete because the configured TLS CA certificate path is missing. Therefore, the correct conclusion is that core tested account functions work, while the legacy tests and Docker TLS configuration require correction before claiming full test success.

### 7.8 Discussion of Results

The implementation demonstrates that the main project objectives have been translated into software components. Central hosting is supported by Docker-node orchestration; sandbox isolation is supported by a unique bridge network per session; resource control is supported by CPU/RAM limits, port reservation, node selection, and expiry cleanup; and educational monitoring is supported by enrolment, progress, submissions, and analytics logs. The current gaps are primarily deployment-hardening and test-maintenance work: valid Docker TLS assets must be installed, a real worker must be tested, stale tests must be updated or removed, and security settings must be changed for production.

### 7.9 System Screenshots

Insert the following screenshots in this order. Each must have a figure number and caption.

1. Home/login page — “Figure 7.1: SomaCloud authentication interface.”
2. Student dashboard — “Figure 7.2: Student dashboard showing learning and lab navigation.”
3. Lab catalogue — “Figure 7.3: Published cybersecurity laboratories grouped by phase.”
4. Lab details — “Figure 7.4: Laboratory theory, tools, challenge and launch controls.”
5. Active sandbox — “Figure 7.5: Browser-based terminal in an isolated sandbox session.”
6. Student analytics — “Figure 7.6: Student progress and recent activity view.”
7. Instructor lab form — “Figure 7.7: Instructor interface for configuring a lab and resource profile.”
8. Instructor monitor — “Figure 7.8: Instructor live monitoring of laboratory sessions.”
9. Administrator control panel — “Figure 7.9: Administration interface for users and platform status.”
10. Docker-node page — “Figure 7.10: Docker worker-node management and health information.”

## Appendix material to add

### Appendix C: Sample resource profiles

| Profile | CPU cores | Memory (MB) | Session limit (minutes) | Intended use |
|---|---:|---:|---:|---|
| Light | 0.25 | 256 | 15 | Basic scanning and enumeration |
| Medium | 0.50 | 512 | 30 | Standard exploitation and brute-force work |
| Heavy | 1.00 | 1024 | 45 | Resource-intensive cracking or web testing |
| Ultra | 2.00 | 2048 | 60 | Multi-target or full network simulation |

### Appendix D: Operational commands

```bash
python manage.py seed_data
python manage.py sync_content
python manage.py expire_sessions
python manage.py verify_node --name <worker-name>
python manage.py test core
```

Never include live passwords, private key contents, Docker TLS keys, setup tokens, real flags, or production IP addresses in the report.
