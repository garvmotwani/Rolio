import json
from datetime import datetime, timedelta
import random

from database.connection import engine, SessionLocal, Base
from models.models import (
    User, Profile, Skill, Experience, Education, Project,
    Company, Job, Resume, SavedJob, Application, Notification,
)
from utils.auth import get_password_hash


def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Demo account so reviewers can log in immediately (README documents these
    # credentials). Runs even when job data is already seeded, but is a no-op
    # once the user exists.
    demo_user_is_new = False
    if not db.query(User).filter(User.email == "demo@rolio.com").first():
        demo_user = User(
            email="demo@rolio.com",
            name="Alex Demo",
            hashed_password=get_password_hash("password"),
            is_active=True,
            is_onboarded=True,
            # Demo account ships pre-verified so the portfolio demo isn't nagged
            email_verified=True,
        )
        db.add(demo_user)
        db.flush()
        demo_profile = Profile(
            user_id=demo_user.id,
            title="Full Stack Developer",
            bio="Full-stack engineer who ships. I build web apps end to end — React frontends on FastAPI backends — and I care about performance and clean code.",
            location="Bengaluru, Karnataka",
            preferred_work_type="hybrid",
            salary_expectation_min=1800000,
            salary_expectation_max=3200000,
            completeness_score=85,
        )
        db.add(demo_profile)
        db.flush()

        for exp in [
            Experience(profile_id=demo_profile.id, company="TechCorp", title="Full Stack Developer",
                       location="Bengaluru, Karnataka", start_date="2022-01", end_date="", is_current=True,
                       description="Built and shipped web apps serving 100K+ users.\nCut API p95 latency 40% by adding caching and query tuning.\nLed migration from REST to typed tRPC-style endpoints."),
            Experience(profile_id=demo_profile.id, company="StartupX", title="Frontend Developer",
                       location="Remote", start_date="2020-06", end_date="2021-12", is_current=False,
                       description="Shipped React UI components used across 4 products.\nImproved Lighthouse performance score from 61 to 94.\nSet up the design system and Storybook."),
        ]:
            db.add(exp)

        db.add(Education(profile_id=demo_profile.id, institution="UC Berkeley", degree="B.S.",
                         field_of_study="Computer Science", start_date="2016-08", end_date="2020-05", gpa="3.7"))

        for name, level, category in [
            ("JavaScript", "advanced", "Languages"), ("TypeScript", "advanced", "Languages"),
            ("Python", "advanced", "Languages"), ("React", "advanced", "Frontend"),
            ("Next.js", "intermediate", "Frontend"), ("Node.js", "intermediate", "Backend"),
            ("FastAPI", "intermediate", "Backend"), ("PostgreSQL", "intermediate", "Data"),
            ("Docker", "intermediate", "DevOps"), ("AWS", "beginner", "DevOps"),
            ("Tailwind CSS", "advanced", "Frontend"), ("GraphQL", "beginner", "Backend"),
        ]:
            db.add(Skill(profile_id=demo_profile.id, name=name, level=level, category=category))

        db.commit()
        demo_user_is_new = True
        print("Seeded demo user with full profile (demo@rolio.com / password).")
    else:
        # Idempotent fix-up: demo users created before email verification
        # existed stay unverified — the demo account should never nag.
        demo = db.query(User).filter(User.email == "demo@rolio.com").first()
        if demo and not demo.email_verified:
            demo.email_verified = True
            db.commit()

    # Check if already seeded
    if db.query(Company).count() > 0:
        if not demo_user_is_new:
            print("Database already seeded.")
        db.close()
        return

    print("Seeding database...")

    # Create companies
    companies_data = [
        {
            "name": "Google",
            "industry": "Technology",
            "location": "Bengaluru, Karnataka",
            "website": "https://google.com",
            "description": "Organizing the world's information and making it universally accessible.",
            "size": "10000+",
            "founded": "1998",
            "logo_url": "https://logo.clearbit.com/google.com",
        },
        {
            "name": "Microsoft",
            "industry": "Technology",
            "location": "Hyderabad, Telangana",
            "website": "https://microsoft.com",
            "description": "Empowering every person and every organization on the planet to achieve more.",
            "size": "10000+",
            "founded": "1975",
            "logo_url": "https://logo.clearbit.com/microsoft.com",
        },
        {
            "name": "Stripe",
            "industry": "FinTech",
            "location": "Bengaluru, Karnataka",
            "website": "https://stripe.com",
            "description": "Financial infrastructure for the internet.",
            "size": "1001-5000",
            "founded": "2010",
            "logo_url": "https://logo.clearbit.com/stripe.com",
        },
        {
            "name": "Notion",
            "industry": "Productivity",
            "location": "Bengaluru, Karnataka",
            "website": "https://notion.so",
            "description": "The all-in-one workspace.",
            "size": "501-1000",
            "founded": "2013",
            "logo_url": "https://logo.clearbit.com/notion.so",
        },
        {
            "name": "Vercel",
            "industry": "Developer Tools",
            "location": "Bengaluru, Karnataka",
            "website": "https://vercel.com",
            "description": "Develop. Preview. Ship.",
            "size": "201-500",
            "founded": "2015",
            "logo_url": "https://logo.clearbit.com/vercel.com",
        },
        {
            "name": "Figma",
            "industry": "Design Tools",
            "location": "Bengaluru, Karnataka",
            "website": "https://figma.com",
            "description": "Where teams design together.",
            "size": "1001-5000",
            "founded": "2012",
            "logo_url": "https://logo.clearbit.com/figma.com",
        },
        {
            "name": "Linear",
            "industry": "Project Management",
            "location": "Bengaluru, Karnataka",
            "website": "https://linear.app",
            "description": "Plan, build, and ship great software.",
            "size": "51-200",
            "founded": "2019",
            "logo_url": "https://logo.clearbit.com/linear.app",
        },
        {
            "name": "Supabase",
            "industry": "Developer Tools",
            "location": "Remote",
            "website": "https://supabase.com",
            "description": "The open source Firebase alternative.",
            "size": "51-200",
            "founded": "2020",
            "logo_url": "https://logo.clearbit.com/supabase.com",
        },
        {
            "name": "Railway",
            "industry": "Cloud Infrastructure",
            "location": "Remote",
            "website": "https://railway.app",
            "description": "Deploy instantly, scale seamlessly.",
            "size": "11-50",
            "founded": "2020",
            "logo_url": "https://logo.clearbit.com/railway.app",
        },
        {
            "name": "Cloudflare",
            "industry": "Internet Infrastructure",
            "location": "Bengaluru, Karnataka",
            "website": "https://cloudflare.com",
            "description": "Helping build a better Internet.",
            "size": "1001-5000",
            "founded": "2009",
            "logo_url": "https://logo.clearbit.com/cloudflare.com",
        },
        {
            "name": "Shopify",
            "industry": "E-Commerce",
            "location": "Pune, Maharashtra",
            "website": "https://shopify.com",
            "description": "Making commerce better for everyone.",
            "size": "10000+",
            "founded": "2006",
            "logo_url": "https://logo.clearbit.com/shopify.com",
        },
        {
            "name": "Datadog",
            "industry": "Observability",
            "location": "Mumbai, Maharashtra",
            "website": "https://datadoghq.com",
            "description": "Monitoring and security for cloud-scale applications.",
            "size": "5001-10000",
            "founded": "2010",
            "logo_url": "https://logo.clearbit.com/datadoghq.com",
        },
        {
            "name": "Figma",
            "industry": "Design Tools",
            "location": "Bengaluru, Karnataka",
            "website": "https://figma.com",
            "description": "Where teams design together.",
            "size": "1001-5000",
            "founded": "2012",
            "logo_url": "https://logo.clearbit.com/figma.com",
        },
        {
            "name": "PostHog",
            "industry": "Analytics",
            "location": "Remote",
            "website": "https://posthog.com",
            "description": "All-in-one product analytics.",
            "size": "51-200",
            "founded": "2020",
            "logo_url": "https://logo.clearbit.com/posthog.com",
        },
    ]

    companies = []
    seen_names = set()
    for cd in companies_data:
        if cd["name"] in seen_names:
            continue
        seen_names.add(cd["name"])
        company = Company(**cd)
        db.add(company)
        companies.append(company)

    db.flush()

    # Create jobs
    now = datetime.utcnow()
    jobs_data = [
        {
            "company": "Google",
            "title": "Senior Software Engineer",
            "description": "Join Google's core engineering team to build scalable systems that serve billions of users. You'll work on distributed systems, large-scale data processing, and cutting-edge technology.",
            "requirements": "5+ years of software development experience. Strong fundamentals in data structures, algorithms, and system design. Proficiency in at least one major programming language.",
            "responsibilities": "Design and implement large-scale distributed systems. Collaborate with cross-functional teams. Mentor junior engineers. Contribute to technical architecture decisions.",
            "preferred_qualifications": "Experience with Google Cloud Platform. Knowledge of Kubernetes and container orchestration. Published research in distributed systems.",
            "skills_required": json.dumps(["Python", "Java", "C++", "System Design", "Distributed Systems"]),
            "skills_preferred": json.dumps(["Kubernetes", "gRPC", "Bigtable", "Cloud"]),
            "location": "Bengaluru, Karnataka",
            "work_type": "hybrid",
            "salary_min": 3200000,
            "salary_max": 5500000,
            "experience_level": "senior",
            "employment_type": "full-time",
        },
        {
            "company": "Google",
            "title": "Frontend Engineer",
            "description": "Build beautiful, accessible, and performant user interfaces for Google products used by millions worldwide.",
            "requirements": "3+ years of frontend development. Deep expertise in JavaScript/TypeScript and modern frameworks. Strong understanding of web performance and accessibility.",
            "responsibilities": "Develop and maintain web applications. Optimize performance and user experience. Write clean, testable code. Collaborate with designers and product managers.",
            "preferred_qualifications": "Experience with Angular or React. Knowledge of web components. Contributions to open-source projects.",
            "skills_required": json.dumps(["JavaScript", "TypeScript", "React", "CSS", "HTML"]),
            "skills_preferred": json.dumps(["Angular", "Web Components", "GraphQL"]),
            "location": "Bengaluru, Karnataka",
            "work_type": "hybrid",
            "salary_min": 1800000,
            "salary_max": 3200000,
            "experience_level": "mid",
            "employment_type": "full-time",
        },
        {
            "company": "Microsoft",
            "title": "Full Stack Developer",
            "description": "Build end-to-end features for Microsoft Teams, impacting over 300 million monthly active users.",
            "requirements": "3+ years of full-stack development. Experience with React and .NET. Understanding of real-time communication technologies.",
            "responsibilities": "Develop frontend and backend features. Design APIs. Write unit and integration tests. Participate in code reviews.",
            "preferred_qualifications": "Experience with SignalR. Knowledge of Azure services. Experience with large-scale applications.",
            "skills_required": json.dumps(["React", "TypeScript", "C#", ".NET", "SQL Server"]),
            "skills_preferred": json.dumps(["SignalR", "Azure", "Microservices"]),
            "location": "Hyderabad, Telangana",
            "work_type": "hybrid",
            "salary_min": 1600000,
            "salary_max": 2800000,
            "experience_level": "mid",
            "employment_type": "full-time",
        },
        {
            "company": "Stripe",
            "title": "Backend Engineer, Payments",
            "description": "Design and build the payment infrastructure that powers millions of businesses worldwide. Work on systems that handle billions of dollars in transactions.",
            "requirements": "4+ years of backend development. Strong knowledge of payment systems, APIs, and distributed systems. Experience with Ruby, Go, or Java.",
            "responsibilities": "Design and implement payment APIs. Build reliable distributed systems. Ensure compliance with financial regulations. Optimize system performance.",
            "preferred_qualifications": "Experience in fintech/payments. Knowledge of PCI compliance. Experience with real-time transaction processing.",
            "skills_required": json.dumps(["Ruby", "Go", "APIs", "Distributed Systems", "PostgreSQL"]),
            "skills_preferred": json.dumps(["Payment Systems", "PCI Compliance", "Kafka"]),
            "location": "Bengaluru, Karnataka",
            "work_type": "hybrid",
            "salary_min": 2800000,
            "salary_max": 4800000,
            "experience_level": "senior",
            "employment_type": "full-time",
        },
        {
            "company": "Stripe",
            "title": "Software Engineer, Risk Platform",
            "description": "Build machine learning systems that detect fraud and protect millions of transactions in real-time.",
            "requirements": "3+ years of software engineering. Experience with ML systems or data pipelines. Proficiency in Python or Go.",
            "responsibilities": "Build ML-powered fraud detection systems. Design data pipelines. Collaborate with data scientists. Improve system accuracy and latency.",
            "preferred_qualifications": "Experience with ML deployment. Knowledge of real-time data processing. Background in security or risk.",
            "skills_required": json.dumps(["Python", "Machine Learning", "Data Pipelines", "APIs"]),
            "skills_preferred": json.dumps(["Go", "Kafka", "TensorFlow", "Fraud Detection"]),
            "location": "Bengaluru, Karnataka",
            "work_type": "hybrid",
            "salary_min": 2200000,
            "salary_max": 4000000,
            "experience_level": "mid",
            "employment_type": "full-time",
        },
        {
            "company": "Notion",
            "title": "Software Engineer, Core Product",
            "description": "Shape the future of productivity tools. Work on Notion's core editor and collaboration features used by millions.",
            "requirements": "3+ years of software development. Strong TypeScript skills. Experience with rich text editors or collaborative software.",
            "responsibilities": "Build and maintain core product features. Improve editor performance. Implement collaboration features. Write technical documentation.",
            "preferred_qualifications": "Experience with ProseMirror or Slate. Knowledge of CRDTs. Contributions to open-source.",
            "skills_required": json.dumps(["TypeScript", "React", "Node.js", "PostgreSQL"]),
            "skills_preferred": json.dumps(["ProseMirror", "CRDTs", "Redis", "Kotlin"]),
            "location": "Bengaluru, Karnataka",
            "work_type": "hybrid",
            "salary_min": 2000000,
            "salary_max": 3600000,
            "experience_level": "mid",
            "employment_type": "full-time",
        },
        {
            "company": "Vercel",
            "title": "Software Engineer, Next.js",
            "description": "Work on Next.js, the most popular React framework. Shape the future of web development for millions of developers.",
            "requirements": "3+ years of web development. Deep understanding of React, Node.js, and web standards. Experience with compiler/transpiler technologies is a plus.",
            "responsibilities": "Develop Next.js features. Improve build performance. Optimize rendering strategies. Collaborate with the open-source community.",
            "preferred_qualifications": "Contributions to Next.js or React. Knowledge of Rust. Experience with edge computing.",
            "skills_required": json.dumps(["TypeScript", "React", "Node.js", "JavaScript"]),
            "skills_preferred": json.dumps(["Rust", "Webpack", "SWC", "Edge Computing"]),
            "location": "Bengaluru, Karnataka",
            "work_type": "remote",
            "salary_min": 2200000,
            "salary_max": 4000000,
            "experience_level": "mid",
            "employment_type": "full-time",
        },
        {
            "company": "Figma",
            "title": "Software Engineer, Rendering",
            "description": "Build the high-performance rendering engine that powers Figma's collaborative design tool in the browser.",
            "requirements": "3+ years of systems or graphics programming. Strong C++ or Rust skills. Understanding of WebGL/WebAssembly.",
            "responsibilities": "Develop and optimize the rendering pipeline. Implement new rendering features. Profile and improve performance. Work on cross-platform compatibility.",
            "preferred_qualifications": "Experience with WebGL or WebGPU. Knowledge of GPU programming. Background in graphics or game engines.",
            "skills_required": json.dumps(["C++", "Rust", "WebGL", "WebAssembly"]),
            "skills_preferred": json.dumps(["WebGPU", "GPU Programming", "TypeScript"]),
            "location": "Bengaluru, Karnataka",
            "work_type": "hybrid",
            "salary_min": 2600000,
            "salary_max": 4500000,
            "experience_level": "senior",
            "employment_type": "full-time",
        },
        {
            "company": "Linear",
            "title": "Founding Engineer",
            "description": "Join Linear as an early engineer. Build the next generation of project management tools from the ground up.",
            "requirements": "4+ years of full-stack development. Strong TypeScript and React skills. Experience building products from scratch.",
            "responsibilities": "Design and build product features. Own features end-to-end. Shape technical architecture. Build a world-class product.",
            "preferred_qualifications": "Experience at an early-stage startup. Knowledge of GraphQL. Passion for developer tools.",
            "skills_required": json.dumps(["TypeScript", "React", "Node.js", "GraphQL", "PostgreSQL"]),
            "skills_preferred": json.dumps(["Electron", "Redis", "Kubernetes"]),
            "location": "Bengaluru, Karnataka",
            "work_type": "remote",
            "salary_min": 2600000,
            "salary_max": 4600000,
            "experience_level": "senior",
            "employment_type": "full-time",
        },
        {
            "company": "Supabase",
            "title": "Software Engineer, Edge Functions",
            "description": "Build the serverless functions platform that runs alongside Supabase's database services.",
            "requirements": "2+ years of backend development. Experience with Deno or Node.js. Understanding of serverless architectures.",
            "responsibilities": "Develop Edge Functions runtime. Build deployment tooling. Improve function performance. Write documentation and examples.",
            "preferred_qualifications": "Experience with Deno. Knowledge of V8 engine. Contributions to open-source.",
            "skills_required": json.dumps(["TypeScript", "Deno", "Node.js", "PostgreSQL"]),
            "skills_preferred": json.dumps(["V8", "WebAssembly", "Docker"]),
            "location": "Remote",
            "work_type": "remote",
            "salary_min": 1800000,
            "salary_max": 3200000,
            "experience_level": "mid",
            "employment_type": "full-time",
        },
        {
            "company": "Cloudflare",
            "title": "Systems Engineer, Workers Runtime",
            "description": "Work on Cloudflare Workers, a serverless execution environment that runs on Cloudflare's global network.",
            "requirements": "3+ systems programming experience. Strong Rust or C/C++ skills. Understanding of JavaScript runtimes and networking.",
            "responsibilities": "Develop the Workers runtime. Optimize V8 isolates. Improve networking performance. Debug complex distributed systems.",
            "preferred_qualifications": "Experience with V8 or JavaScriptCore. Knowledge of WebAssembly. Contributions to browser engines.",
            "skills_required": json.dumps(["Rust", "C++", "JavaScript", "Networking"]),
            "skills_preferred": json.dumps(["V8", "WebAssembly", "Linux Kernel", "eBPF"]),
            "location": "Bengaluru, Karnataka",
            "work_type": "hybrid",
            "salary_min": 2500000,
            "salary_max": 4200000,
            "experience_level": "senior",
            "employment_type": "full-time",
        },
        {
            "company": "Shopify",
            "title": "Ruby on Rails Developer",
            "description": "Build commerce infrastructure on one of the largest Rails applications in the world.",
            "requirements": "3+ years of Ruby on Rails development. Strong database skills. Experience with large-scale applications.",
            "responsibilities": "Develop commerce features. Optimize database queries. Write comprehensive tests. Participate in architecture decisions.",
            "preferred_qualifications": "Experience with Hotwire/Turbo. Knowledge of GraphQL. Experience with large-scale Rails apps.",
            "skills_required": json.dumps(["Ruby", "Rails", "PostgreSQL", "JavaScript", "HTML"]),
            "skills_preferred": json.dumps(["Hotwire", "GraphQL", "Redis", "Kafka"]),
            "location": "Pune, Maharashtra",
            "work_type": "hybrid",
            "salary_min": 1800000,
            "salary_max": 3000000,
            "experience_level": "mid",
            "employment_type": "full-time",
        },
        {
            "company": "Datadog",
            "title": "Data Engineer",
            "description": "Build data pipelines that process trillions of data points per day for monitoring and observability.",
            "requirements": "3+ years of data engineering. Strong SQL and Python skills. Experience with large-scale data processing.",
            "responsibilities": "Design and build data pipelines. Optimize query performance. Work with streaming data systems. Ensure data quality and reliability.",
            "preferred_qualifications": "Experience with Spark or Flink. Knowledge of time-series databases. Experience with Kafka.",
            "skills_required": json.dumps(["Python", "SQL", "Apache Spark", "Kafka", "AWS"]),
            "skills_preferred": json.dumps(["Flink", "ClickHouse", "Docker", "Terraform"]),
            "location": "Mumbai, Maharashtra",
            "work_type": "hybrid",
            "salary_min": 2000000,
            "salary_max": 3500000,
            "experience_level": "mid",
            "employment_type": "full-time",
        },
        {
            "company": "PostHog",
            "title": "Product Engineer",
            "description": "Build product analytics features that help thousands of companies understand their users.",
            "requirements": "3+ years of full-stack development. Strong Python and TypeScript skills. Experience with product analytics or data systems.",
            "responsibilities": "Build analytics features end-to-end. Design data models. Write Django and React code. Deploy to production frequently.",
            "preferred_qualifications": "Experience with ClickHouse. Knowledge of event processing. Contributions to open-source.",
            "skills_required": json.dumps(["Python", "Django", "TypeScript", "React", "PostgreSQL"]),
            "skills_preferred": json.dumps(["ClickHouse", "Kafka", "Docker", "Kubernetes"]),
            "location": "Remote",
            "work_type": "remote",
            "salary_min": 1600000,
            "salary_max": 2800000,
            "experience_level": "mid",
            "employment_type": "full-time",
        },
        {
            "company": "Railway",
            "title": "Backend Engineer, Infrastructure",
            "description": "Build the infrastructure platform that makes deploying applications effortless for developers.",
            "requirements": "3+ years of backend development. Strong Go or Python skills. Experience with container orchestration and cloud infrastructure.",
            "responsibilities": "Design deployment infrastructure. Build internal tooling. Improve system reliability. Work on scaling systems.",
            "preferred_qualifications": "Experience with Kubernetes. Knowledge of networking. Background in DevOps or platform engineering.",
            "skills_required": json.dumps(["Go", "Python", "Docker", "Kubernetes", "Linux"]),
            "skills_preferred": json.dumps(["Nix", "Terraform", "gRPC", "Prometheus"]),
            "location": "Remote",
            "work_type": "remote",
            "salary_min": 2200000,
            "salary_max": 3600000,
            "experience_level": "senior",
            "employment_type": "full-time",
        },
        {
            "company": "Google",
            "title": "Machine Learning Engineer",
            "description": "Develop and deploy machine learning models that power Google Search and other core products.",
            "requirements": "3+ years of ML engineering experience. Strong Python and TensorFlow skills. Experience with large-scale ML systems.",
            "responsibilities": "Design and train ML models. Build data pipelines. Deploy models to production. Monitor model performance.",
            "preferred_qualifications": "Experience with JAX. Published ML research. Knowledge of NLP or computer vision.",
            "skills_required": json.dumps(["Python", "TensorFlow", "Machine Learning", "SQL", "Data Pipelines"]),
            "skills_preferred": json.dumps(["JAX", "PyTorch", "Kubernetes", "BigQuery"]),
            "location": "Bengaluru, Karnataka",
            "work_type": "hybrid",
            "salary_min": 2800000,
            "salary_max": 5200000,
            "experience_level": "senior",
            "employment_type": "full-time",
        },
        {
            "company": "Microsoft",
            "title": "DevOps Engineer",
            "description": "Build and maintain CI/CD pipelines for Azure DevOps, ensuring reliable delivery for millions of developers.",
            "requirements": "3+ years of DevOps experience. Strong skills in Azure, PowerShell, and automation. Experience with CI/CD tools.",
            "responsibilities": "Design and maintain CI/CD pipelines. Automate infrastructure. Monitor system health. Respond to incidents.",
            "preferred_qualifications": "Experience with GitHub Actions. Knowledge of Terraform. Azure certifications.",
            "skills_required": json.dumps(["Azure", "PowerShell", "CI/CD", "Docker", "Linux"]),
            "skills_preferred": json.dumps(["Terraform", "Kubernetes", "GitHub Actions", "Python"]),
            "location": "Hyderabad, Telangana",
            "work_type": "hybrid",
            "salary_min": 1700000,
            "salary_max": 3000000,
            "experience_level": "mid",
            "employment_type": "full-time",
        },
        {
            "company": "Stripe",
            "title": "Junior Software Engineer",
            "description": "Start your career at Stripe working on payment infrastructure. Great mentorship and growth opportunities.",
            "requirements": "0-2 years of development experience. Strong fundamentals in CS. Proficiency in at least one programming language.",
            "responsibilities": "Build features under guidance. Write clean, tested code. Learn from senior engineers. Contribute to team projects.",
            "preferred_qualifications": "CS degree or bootcamp graduate. Open-source contributions. Strong problem-solving skills.",
            "skills_required": json.dumps(["Python", "JavaScript", "SQL", "Git"]),
            "skills_preferred": json.dumps(["Ruby", "Go", "React", "REST APIs"]),
            "location": "Bengaluru, Karnataka",
            "work_type": "hybrid",
            "salary_min": 800000,
            "salary_max": 1400000,
            "experience_level": "junior",
            "employment_type": "full-time",
        },
        {
            "company": "Notion",
            "title": "Senior Product Designer",
            "description": "Design the future of productivity. Shape how millions of people organize their work and lives.",
            "requirements": "5+ years of product design experience. Strong Figma skills. Portfolio demonstrating complex product thinking.",
            "responsibilities": "Lead design for product features. Create prototypes and wireframes. Collaborate with engineering. Conduct user research.",
            "preferred_qualifications": "Experience designing for developer tools. Knowledge of design systems. Strong interaction design skills.",
            "skills_required": json.dumps(["Figma", "Prototyping", "User Research", "Design Systems"]),
            "skills_preferred": json.dumps(["CSS", "HTML", "Motion Design", "Accessibility"]),
            "location": "Bengaluru, Karnataka",
            "work_type": "hybrid",
            "salary_min": 2200000,
            "salary_max": 3800000,
            "experience_level": "senior",
            "employment_type": "full-time",
        },
        {
            "company": "Vercel",
            "title": "Senior Software Engineer, Infrastructure",
            "description": "Build the deployment infrastructure that powers millions of websites and applications.",
            "requirements": "5+ years of systems or infrastructure engineering. Strong Go or Rust skills. Experience with distributed systems.",
            "responsibilities": "Design and build deployment systems. Optimize build performance. Improve platform reliability. Scale infrastructure globally.",
            "preferred_qualifications": "Experience with edge computing. Knowledge of CDN architectures. Contributions to open-source infrastructure.",
            "skills_required": json.dumps(["Go", "Rust", "Docker", "Kubernetes", "Linux"]),
            "skills_preferred": json.dumps(["Terraform", "Prometheus", "gRPC", "Cloudflare Workers"]),
            "location": "Bengaluru, Karnataka",
            "work_type": "remote",
            "salary_min": 3000000,
            "salary_max": 5200000,
            "experience_level": "senior",
            "employment_type": "full-time",
        },
        {
            "company": "Google",
            "title": "Software Engineering Intern",
            "description": "Work alongside experienced engineers on real Google projects during this 10-12 week summer internship. Contribute to production code from day one.",
            "requirements": "Pursuing a B.Tech/M.Tech in Computer Science or related field. Strong fundamentals in data structures and algorithms. Proficiency in Python, Java, or C++.",
            "responsibilities": "Contribute to production codebases. Participate in code reviews. Collaborate with the team on feature development. Present your project at the end of the internship.",
            "preferred_qualifications": "Competitive programming experience. Strong academic record. Prior internship or open-source experience.",
            "skills_required": json.dumps(["Python", "Data Structures", "Algorithms", "Git"]),
            "skills_preferred": json.dumps(["Java", "C++", "System Design"]),
            "location": "Bengaluru, Karnataka",
            "work_type": "hybrid",
            "salary_min": 120000,
            "salary_max": 150000,
            "experience_level": "intern",
            "employment_type": "internship",
        },
        {
            "company": "Microsoft",
            "title": "Product Engineering Intern",
            "description": "Join Microsoft's engineering team in Hyderabad for a hands-on internship building features used by millions of users.",
            "requirements": "Pre-final year student in CS/IT. Problem-solving skills and familiarity with at least one programming language.",
            "responsibilities": "Build and ship a feature with mentorship. Write tests. Collaborate in an agile team. Learn Microsoft's engineering culture.",
            "preferred_qualifications": "Hackathon participation. Exposure to cloud platforms.",
            "skills_required": json.dumps(["C#", "JavaScript", "SQL", "Problem Solving"]),
            "skills_preferred": json.dumps(["Azure", "React", "REST APIs"]),
            "location": "Hyderabad, Telangana",
            "work_type": "hybrid",
            "salary_min": 100000,
            "salary_max": 130000,
            "experience_level": "intern",
            "employment_type": "internship",
        },
        {
            "company": "Stripe",
            "title": "Backend Engineering Intern",
            "description": "Intern with Stripe's payments infrastructure team in Bengaluru. Work on systems processing millions of transactions.",
            "requirements": "Strong programming fundamentals in Python, Go, or Java. Understanding of data structures and APIs. Available for a 3-6 month full-time internship.",
            "responsibilities": "Ship real backend features. Write reliable, tested code. Learn distributed systems from experienced mentors.",
            "preferred_qualifications": "Interest in fintech infrastructure. Experience with side projects.",
            "skills_required": json.dumps(["Python", "Go", "APIs", "SQL"]),
            "skills_preferred": json.dumps(["Distributed Systems", "Redis", "Docker"]),
            "location": "Bengaluru, Karnataka",
            "work_type": "hybrid",
            "salary_min": 150000,
            "salary_max": 200000,
            "experience_level": "intern",
            "employment_type": "internship",
        },
        {
            "company": "Cloudflare",
            "title": "Security Engineer",
            "description": "Protect millions of websites from attacks. Build security systems at internet scale.",
            "requirements": "4+ years of security engineering. Strong networking knowledge. Experience with security tools and frameworks.",
            "responsibilities": "Design security architectures. Investigate vulnerabilities. Build detection systems. Respond to security incidents.",
            "preferred_qualifications": "Experience with DDoS mitigation. Knowledge of TLS/SSL. Security certifications.",
            "skills_required": json.dumps(["Python", "Go", "Networking", "Security", "Linux"]),
            "skills_preferred": json.dumps(["Rust", "eBPF", "IDS/IPS", "SIEM"]),
            "location": "Bengaluru, Karnataka",
            "work_type": "hybrid",
            "salary_min": 2400000,
            "salary_max": 4200000,
            "experience_level": "senior",
            "employment_type": "full-time",
        },
    ]

    company_map = {c.name: c.id for c in companies}
    jobs = []
    for i, jd in enumerate(jobs_data):
        company_id = company_map.get(jd["company"])
        if not company_id:
            continue
        job = Job(
            company_id=company_id,
            title=jd["title"],
            description=jd["description"],
            requirements=jd["requirements"],
            responsibilities=jd["responsibilities"],
            preferred_qualifications=jd["preferred_qualifications"],
            skills_required=jd["skills_required"],
            skills_preferred=jd["skills_preferred"],
            location=jd["location"],
            work_type=jd["work_type"],
            salary_min=jd["salary_min"],
            salary_max=jd["salary_max"],
            experience_level=jd["experience_level"],
            employment_type=jd["employment_type"],
            posted_at=now - timedelta(days=random.randint(1, 30)),
        )
        db.add(job)
        jobs.append(job)

    db.commit()
    print(f"Seeded {len(companies)} companies and {len(jobs)} jobs.")
    db.close()


if __name__ == "__main__":
    seed_database()
