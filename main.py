import streamlit as st
import http.client
import json
import os
import PyPDF2
import io
from google import genai
import requests
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

# Configure page
st.set_page_config(page_title="AI Job Finder", page_icon="💼", layout="wide")

# Styling
st.markdown("""
<style>
    /* Global typography */
    body {
        font-family: 'Inter', sans-serif;
    }
    
    /* Headers */
    .main-header {
        font-size: 2.8rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
        background: linear-gradient(90deg, #1E3A8A, #3B82F6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .sub-header {
        font-size: 1.2rem;
        color: #64748B;
        margin-bottom: 2rem;
        font-weight: 400;
    }
    
    /* Section headers */
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1E3A8A;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #E2E8F0;
    }
    
    /* Cards and containers */
    .card {
        background-color: #FFFFFF;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        border: 1px solid #E2E8F0;
    }
    
    .info-box {
        background-color: #EFF6FF;
        border-left: 6px solid #3B82F6;
        padding: 1rem;
        border-radius: 4px;
        margin-bottom: 1.5rem;
    }
    
    /* Messages */
    .success-message {
        background-color: #ECFDF5;
        color: #065F46;
        padding: 1rem;
        border-radius: 4px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
    }
    
    .success-message:before {
        content: "✅";
        margin-right: 0.75rem;
        font-size: 1.2rem;
    }
    
    .warning-message {
        background-color: #FFFBEB;
        color: #92400E;
        padding: 1rem;
        border-radius: 4px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
    }
    
    .warning-message:before {
        content: "⚠️";
        margin-right: 0.75rem;
        font-size: 1.2rem;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #3B82F6;
        color: white;
        font-weight: 500;
        border-radius: 6px;
        padding: 0.5rem 1.5rem;
        transition: all 0.2s ease;
    }
    
    .stButton>button:hover {
        background-color: #1D4ED8;
        box-shadow: 0 4px 6px rgba(29, 78, 216, 0.15);
    }
    
    /* Job listings */
    .job-card {
        border-left: 5px solid #3B82F6;
        background-color: #F8FAFC;
        padding: 1rem;
        margin-bottom: 1rem;
        border-radius: 0 4px 4px 0;
    }
    
    .job-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #1E3A8A;
        margin-bottom: 0.5rem;
    }
    
    .job-company {
        font-size: 1rem;
        color: #64748B;
        margin-bottom: 0.5rem;
    }
    
    .job-detail {
        display: flex;
        align-items: center;
        margin-bottom: 0.3rem;
        font-size: 0.9rem;
    }
    
    .job-detail:before {
        content: "•";
        color: #3B82F6;
        margin-right: 0.5rem;
    }
    
    /* Match indicators */
    .match-indicator {
        background-color: #F0F9FF;
        border-radius: 6px;
        padding: 1rem;
    }
    
    .match-high {
        color: #047857;
        font-weight: 600;
    }
    
    .match-medium {
        color: #B45309;
        font-weight: 600;
    }
    
    .match-low {
        color: #DC2626;
        font-weight: 600;
    }
    
    .skill-tag {
        display: inline-block;
        background-color: #E0F2FE;
        color: #0369A1;
        font-size: 0.8rem;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    /* Form elements */
    .stTextInput>div>div>input {
        border-radius: 6px;
        border: 1px solid #CBD5E1;
    }
    
    .stFileUploader>div>button {
        background-color: #F1F5F9;
        color: #475569;
        border-radius: 6px;
    }
    
    /* Sidebar */
    .sidebar .sidebar-content {
        background-color: #F8FAFC;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #1E3A8A;
        background-color: #F1F5F9;
        border-radius: 4px;
    }
    
    /* Dividers */
    hr {
        margin: 2rem 0;
        border: 0;
        height: 1px;
        background: #E2E8F0;
    }
    
    /* Progress bar */
    .stProgress > div > div > div > div {
        background-color: #3B82F6;
    }
    
    /* Metrics */
    .metric-card {
        background-color: #F1F5F9;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1E3A8A;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #64748B;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<p class="main-header">AI-Powered Job Finder</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Upload your resume and find relevant jobs tailored to your skills and experience</p>', unsafe_allow_html=True)

# Initialize session state variables
if 'resume_text' not in st.session_state:
    st.session_state.resume_text = ""
if 'resume_parsed' not in st.session_state:
    st.session_state.resume_parsed = False
if 'parsed_data' not in st.session_state:
    st.session_state.parsed_data = {}
if 'job_results' not in st.session_state:
    st.session_state.job_results = []
if 'search_completed' not in st.session_state:
    st.session_state.search_completed = False

# Define the JSON schema for resume parsing
RESUME_SCHEMA = {
    "schema": {
        "basic_info": {
            "name": "string",
            "email": "string",
            "phone": "string",
            "location": "string"
        },
        "professional_summary": "string",
        "skills": ["string"],
        "technical_skills": ["string"],
        "soft_skills": ["string"],
        "experience": [{
            "job_title": "string",
            "company": "string",
            "duration": "string",
            "description": "string"
        }],
        "education": [{
            "degree": "string",
            "institution": "string",
            "year": "string"
        }],
        "certifications": ["string"],
        "years_of_experience": "number"
    }
}

# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page_num in range(len(pdf_reader.pages)):
        text += pdf_reader.pages[page_num].extract_text()
    return text

# Function to parse resume with Gemini
def parse_resume_with_gemini(resume_text):
    try:
        # Configure the Gemini API
        client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        
        # Construct the prompt with schema
        prompt = f"""
        Parse the following resume text and extract information according to this exact JSON schema:
        
        {json.dumps(RESUME_SCHEMA, indent=2)}
        
        Resume text:
        {resume_text}
        
        Make sure to follow the schema exactly. If any information is not available, use empty strings or empty arrays as appropriate.
        Return ONLY the JSON object with no additional text.
        """
        
        # Generate the response
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        
        # Parse the response to get JSON
        try:
            parsed_data = json.loads(response.text)
            return parsed_data
        except json.JSONDecodeError:
            # Try to extract JSON from the text if not directly parseable
            import re
            json_match = re.search(r'```json\n(.*?)\n```', response.text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            else:
                st.error("Could not parse the response as JSON")
                return RESUME_SCHEMA["schema"]
    except Exception as e:
        st.error(f"Error parsing resume: {str(e)}")
        return RESUME_SCHEMA["schema"]

# Function to search for jobs
def search_jobs(query, location="", page=1):
    try:
        conn = http.client.HTTPSConnection("jsearch.p.rapidapi.com")
        
        # Format the query string
        search_query = query.replace(" ", "%20")
        if location:
            search_query += f"%20in%20{location.replace(' ', '%20')}"
        
        headers = {
            'X-RapidAPI-Key': os.getenv('RAPIDAPI_KEY'),
            'X-RapidAPI-Host': "jsearch.p.rapidapi.com"
        }
        
        conn.request("GET", f"/search?query={search_query}&page={page}&num_pages=1", headers=headers)
        
        res = conn.getresponse()
        data = res.read()
        
        return json.loads(data.decode("utf-8"))
    except Exception as e:
        st.error(f"Error searching for jobs: {str(e)}")
        return {"data": []}

if 'filter_remote_only' not in st.session_state:
    st.session_state.filter_remote_only = False
if 'filter_employment_types' not in st.session_state:
    st.session_state.filter_employment_types = []
if 'filter_date_posted' not in st.session_state:
    st.session_state.filter_date_posted = 0
if 'min_salary' not in st.session_state:
    st.session_state.min_salary = 0
if 'max_salary' not in st.session_state:
    st.session_state.max_salary = 1000000
if 'filter_company_types' not in st.session_state:
    st.session_state.filter_company_types = []
    
# Function to apply filters to job results
def apply_filters(jobs):
    filtered_jobs = []
    
    for job in jobs:
        # Check remote filter
        if st.session_state.filter_remote_only and not job.get('job_is_remote', False):
            continue
            
        # Check employment type filter
        if st.session_state.filter_employment_types and job.get('job_employment_type') not in st.session_state.filter_employment_types:
            continue
            
        # Check date posted filter (in days)
        if st.session_state.filter_date_posted > 0:
            current_time = int(time.time())
            posted_time = job.get('job_posted_at_timestamp', 0)
            days_ago = (current_time - posted_time) / (60 * 60 * 24)
            if days_ago > st.session_state.filter_date_posted:
                continue
                
        # Check salary filter
        if job.get('job_min_salary') is not None and job.get('job_min_salary') < st.session_state.min_salary:
            continue
            
        if job.get('job_max_salary') is not None and job.get('job_max_salary') > st.session_state.max_salary:
            continue
            
        # Check company type filter
        if st.session_state.filter_company_types and job.get('employer_company_type') not in st.session_state.filter_company_types:
            continue
            
        # All filters passed, add job to filtered results
        filtered_jobs.append(job)
        
    return filtered_jobs

# Main layout
col1, col2 = st.columns([3, 1])

with col1:
    # Resume Upload Section
    st.markdown('<p class="section-header">📄 Upload Your Resume</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="info-box">Upload your resume to enable AI-powered job matching based on your skills and experience</div>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Upload your resume (PDF format)", type=['pdf'])

    if uploaded_file is not None:
        with st.spinner('Processing your resume...'):
            # Extract text from the PDF
            resume_text = extract_text_from_pdf(uploaded_file)
            st.session_state.resume_text = resume_text
            
            # Parse the resume
            parsed_data = parse_resume_with_gemini(resume_text)
            st.session_state.parsed_data = parsed_data
            st.session_state.resume_parsed = True
            
            # Display success message
            st.markdown('<div class="success-message">Resume successfully parsed!</div>', unsafe_allow_html=True)
            
            # Display the parsed information
            with st.expander("View Parsed Resume Information", expanded=True):
                tab1, tab2, tab3 = st.tabs(["Basic Info", "Experience", "Skills & Education"])
                
                with tab1:
                    # Basic information card
                    basic_info = parsed_data.get("basic_info", {})
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Name:** {basic_info.get('name', 'Not found')}")
                        st.markdown(f"**Email:** {basic_info.get('email', 'Not found')}")
                    
                    with col2:
                        st.markdown(f"**Phone:** {basic_info.get('phone', 'Not found')}")
                        st.markdown(f"**Location:** {basic_info.get('location', 'Not found')}")
                    
                    if parsed_data.get("professional_summary"):
                        st.markdown("<hr style='margin: 1rem 0'>", unsafe_allow_html=True)
                        st.markdown("**Professional Summary:**")
                        st.markdown(parsed_data.get("professional_summary", ""))
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with tab2:
                    if parsed_data.get("experience"):
                        for exp in parsed_data.get("experience", []):
                            st.markdown('<div class="card">', unsafe_allow_html=True)
                            st.markdown(f"<div style='color: #1E3A8A; font-weight: 600; font-size: 1.1rem;'>{exp.get('job_title', 'Role')}</div>", unsafe_allow_html=True)
                            st.markdown(f"<div style='color: #64748B; font-weight: 500;'>{exp.get('company', 'Company')}</div>", unsafe_allow_html=True)
                            st.markdown(f"<div style='color: #94A3B8; font-size: 0.9rem; margin-bottom: 0.75rem;'>{exp.get('duration', 'Duration not specified')}</div>", unsafe_allow_html=True)
                            st.markdown(exp.get('description', 'No description available'))
                            st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.info("No experience information found in your resume")
                
                with tab3:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown('<div class="card">', unsafe_allow_html=True)
                        st.markdown("<strong>Skills</strong>")
                        
                        # Technical skills
                        st.markdown("**Technical Skills:**")
                        tech_skills = parsed_data.get("technical_skills", [])
                        if tech_skills:
                            for skill in tech_skills:
                                st.markdown(f"<span class='skill-tag'>{skill}</span>", unsafe_allow_html=True)
                        else:
                            st.markdown("No technical skills found")
                        
                        # Soft skills
                        st.markdown("<div style='margin-top: 1rem;'>**Soft Skills:**</div>", unsafe_allow_html=True)
                        soft_skills = parsed_data.get("soft_skills", [])
                        if soft_skills:
                            for skill in soft_skills:
                                st.markdown(f"<span class='skill-tag'>{skill}</span>", unsafe_allow_html=True)
                        else:
                            st.markdown("No soft skills found")
                        
                        # General skills
                        st.markdown("<div style='margin-top: 1rem;'>**General Skills:**</div>", unsafe_allow_html=True)
                        skills = parsed_data.get("skills", [])
                        if skills:
                            for skill in skills:
                                st.markdown(f"<span class='skill-tag'>{skill}</span>", unsafe_allow_html=True)
                        else:
                            st.markdown("No general skills found")
                            
                        st.markdown(f"<div style='margin-top: 1rem;'>**Years of Experience:** {parsed_data.get('years_of_experience', 'Not specified')}</div>", unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown('<div class="card">', unsafe_allow_html=True)
                        st.markdown("<strong>Education</strong>")
                        
                        for edu in parsed_data.get("education", []):
                            st.markdown(f"<div style='margin-bottom: 1rem;'>", unsafe_allow_html=True)
                            st.markdown(f"<div style='font-weight: 600;'>{edu.get('degree', 'Degree')}</div>", unsafe_allow_html=True)
                            st.markdown(f"<div>{edu.get('institution', 'Institution')}</div>", unsafe_allow_html=True)
                            st.markdown(f"<div style='color: #94A3B8; font-size: 0.9rem;'>{edu.get('year', 'Year not specified')}</div>", unsafe_allow_html=True)
                            st.markdown("</div>", unsafe_allow_html=True)
                            
                        # Certifications if available
                        if parsed_data.get("certifications"):
                            st.markdown("<hr style='margin: 1rem 0'>", unsafe_allow_html=True)
                            st.markdown("<strong>Certifications</strong>")
                            for cert in parsed_data.get("certifications", []):
                                st.markdown(f"• {cert}")
                        
                        st.markdown('</div>', unsafe_allow_html=True)

    # Job Search Section
    st.markdown('<p class="section-header">🔍 Search for Jobs</p>', unsafe_allow_html=True)
    
    # Search form with improved styling
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    search_query = st.text_input("Job Title", placeholder="e.g., Python Developer, Product Manager")
    
    col1, col2 = st.columns(2)
    with col1:
        location = st.text_input("Location", placeholder="e.g., New York, Remote")
    with col2:
        search_button = st.button("Search Jobs", use_container_width=True)
    
    if st.session_state.resume_parsed:
        st.markdown('<div class="success-message">Resume skills will be used for job matching</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if search_button:
        if search_query:
            with st.spinner('Searching for relevant jobs...'):
                # Search for jobs
                job_results = search_jobs(search_query, location)
                
                # Store the results in session state
                st.session_state.job_results = job_results.get('data', [])
                st.session_state.search_completed = True
        else:
            st.markdown('<div class="warning-message">Please enter a job title to search</div>', unsafe_allow_html=True)

with col2:
    # Filter sidebar
    st.markdown('<p class="section-header">⚙️ Filters</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    # Remote work filter
    st.checkbox("Remote Only", key="filter_remote_only")
    
    # Employment type filter
    st.markdown("<div style='margin-top: 1rem;'><strong>Employment Type</strong></div>", unsafe_allow_html=True)
    employment_types = ["FULLTIME", "PARTTIME", "CONTRACTOR", "INTERN"]
    st.multiselect(
        "Select types", 
        employment_types,
        default=None,
        key="filter_employment_types",
        label_visibility="collapsed"
    )
    
    # Date posted filter
    st.markdown("<div style='margin-top: 1rem;'><strong>Date Posted</strong></div>", unsafe_allow_html=True)
    date_options = {
        "Any time": 0,
        "Past 24 hours": 1,
        "Past week": 7,
        "Past month": 30
    }
    selected_date = st.selectbox(
        "Select timeframe",
        options=list(date_options.keys()),
        index=0,
        label_visibility="collapsed"
    )
    st.session_state.filter_date_posted = date_options[selected_date]
    
    # Salary range filter
    st.markdown("<div style='margin-top: 1rem;'><strong>Salary Range</strong></div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.number_input("Min (₹)", value=0, step=10000, key="min_salary")
    with col2:
        st.number_input("Max (₹)", value=1000000, step=10000, key="max_salary")
    
    # Company type filter
    st.markdown("<div style='margin-top: 1rem;'><strong>Company Type</strong></div>", unsafe_allow_html=True)
    company_types = ["Public", "Private", "Nonprofit", "Government", "Startup", "Other"]
    st.multiselect(
        "Select types",
        company_types,
        default=None,
        key="filter_company_types",
        label_visibility="collapsed"
    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # App metrics
    st.markdown('<p class="section-header">📊 Stats</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        if st.session_state.resume_parsed:
            skill_count = len(st.session_state.parsed_data.get("skills", [])) + len(st.session_state.parsed_data.get("technical_skills", []))
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{skill_count}</div>', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Skills</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="metric-card" style="opacity: 0.5">', unsafe_allow_html=True)
            st.markdown('<div class="metric-value">-</div>', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Skills</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        if st.session_state.search_completed:
            job_count = len(st.session_state.job_results)
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{job_count}</div>', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Jobs</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="metric-card" style="opacity: 0.5">', unsafe_allow_html=True)
            st.markdown('<div class="metric-value">-</div>', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Jobs</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Display Results
if st.session_state.search_completed:
    st.markdown('<p class="section-header">🎯 Job Matches</p>', unsafe_allow_html=True)
    
    if st.session_state.job_results:
        # Apply filters
        filtered_jobs = apply_filters(st.session_state.job_results)
        
        if filtered_jobs:
            st.markdown(f'<div class="success-message">Found {len(filtered_jobs)} jobs matching your criteria</div>', unsafe_allow_html=True)
            
            # Calculate skill match percentages if resume is uploaded
            if st.session_state.resume_parsed:
                # Extract all skills from resume
                tech_skills = set(st.session_state.parsed_data.get("technical_skills", []))
                general_skills = set(st.session_state.parsed_data.get("skills", []))
                soft_skills = set(st.session_state.parsed_data.get("soft_skills", []))
                all_skills = tech_skills.union(general_skills).union(soft_skills)
                
                # Add match score to each job
                for job in filtered_jobs:
                    if job.get('job_description'):
                        desc = job.get('job_description', '').lower()
                        matched_skills = [skill for skill in all_skills if skill.lower() in desc]
                        match_percentage = int((len(matched_skills) / max(1, len(all_skills))) * 100)
                        job['match_percentage'] = match_percentage
                        job['matched_skills'] = matched_skills
                    else:
                        job['match_percentage'] = 0
                        job['matched_skills'] = []
                
                # Option to sort by match percentage
                col1, col2 = st.columns([1, 2])
                with col1:
                    sort_by_match = st.checkbox("Sort by match percentage", value=True)
                
                if sort_by_match:
                    filtered_jobs = sorted(filtered_jobs, key=lambda x: x.get('match_percentage', 0), reverse=True)
            
            for job_idx, job in enumerate(filtered_jobs):
                # Create a job card
                st.markdown('<div class="card job-card">', unsafe_allow_html=True)
                
                # Job header
                cols = st.columns([3, 1])
                
                with cols[0]:
                    if st.session_state.resume_parsed and 'match_percentage' in job:
                        match_percentage = job.get('match_percentage', 0)
                        if match_percentage > 70:
                            match_class = "match-high"
                        elif match_percentage > 40:
                            match_class = "match-medium"
                        else:
                            match_class = "match-low"
                            
                        st.markdown(f"<div style='display: flex; align-items: center;'>", unsafe_allow_html=True)
                        st.markdown(f"<div class='job-title'>{job.get('job_title', 'Job Title Not Available')}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='margin-left: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8rem;' class='{match_class}'>{match_percentage}% Match</div>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='job-title'>{job.get('job_title', 'Job Title Not Available')}</div>", unsafe_allow_html=True)
                    
                    st.markdown(f"<div class='job-company'>{job.get('employer_name', 'Company Not Available')}</div>", unsafe_allow_html=True)