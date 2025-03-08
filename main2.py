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
    .main-header {
        font-size: 2.5rem;
        color: #4169E1;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #6C757D;
    }
    .success-message {
        background-color: #D4EDDA;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    .info-box {
        background-color: #E7F3FE;
        border-left: 6px solid #2196F3;
        padding: 10px;
        margin-bottom: 15px;
    }
    .search-options {
        margin-top: 20px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<p class="main-header">AI-Powered Job Finder</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Upload your resume and find relevant jobs</p>', unsafe_allow_html=True)

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
        
        # Get the model
        
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

# Resume Upload Section
st.subheader("Step 1: Upload Your Resume First")
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
        
        # Display the parsed information
        with st.expander("Resume Parsed Information", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Basic Information")
                basic_info = parsed_data.get("basic_info", {})
                st.write(f"**Name:** {basic_info.get('name', 'Not found')}")
                st.write(f"**Email:** {basic_info.get('email', 'Not found')}")
                st.write(f"**Phone:** {basic_info.get('phone', 'Not found')}")
                st.write(f"**Location:** {basic_info.get('location', 'Not found')}")
                
                st.markdown("### Experience")
                for exp in parsed_data.get("experience", []):
                    st.markdown(f"**{exp.get('job_title', 'Role')} at {exp.get('company', 'Company')}**")
                    st.write(f"*{exp.get('duration', 'Duration not specified')}*")
                    st.write(exp.get('description', 'No description available'))
                    st.write("---")
            
            with col2:
                st.markdown("### Skills")
                
                # Technical skills
                st.write("**Technical Skills:**")
                tech_skills = parsed_data.get("technical_skills", [])
                if tech_skills:
                    st.write(", ".join(tech_skills))
                else:
                    st.write("No technical skills found")
                
                # Soft skills
                st.write("**Soft Skills:**")
                soft_skills = parsed_data.get("soft_skills", [])
                if soft_skills:
                    st.write(", ".join(soft_skills))
                else:
                    st.write("No soft skills found")
                
                # General skills
                st.write("**General Skills:**")
                skills = parsed_data.get("skills", [])
                if skills:
                    st.write(", ".join(skills))
                else:
                    st.write("No general skills found")
                
                st.markdown("### Education")
                for edu in parsed_data.get("education", []):
                    st.write(f"**{edu.get('degree', 'Degree')}** - {edu.get('institution', 'Institution')}")
                    st.write(f"*{edu.get('year', 'Year not specified')}*")
                
                st.write(f"**Years of Experience:** {parsed_data.get('years_of_experience', 'Not specified')}")
st.markdown("---")
st.subheader("Step 2: Search for Jobs")

# Query input
search_query = st.text_input("Enter your job search query (e.g., 'Python Developer')")
location = st.text_input("Location (e.g., 'New York', 'Remote')")

# Add filter options to sidebar
st.sidebar.markdown("### Filter Options")

# Remote work filter
st.sidebar.checkbox("Remote Only", key="filter_remote_only")

# Employment type filter
employment_types = ["FULLTIME", "PARTTIME", "CONTRACTOR", "INTERN"]
st.sidebar.multiselect(
    "Employment Type", 
    employment_types,
    default=None,
    key="filter_employment_types"
)

# Date posted filter
date_options = {
    "Any time": 0,
    "Past 24 hours": 1,
    "Past week": 7,
    "Past month": 30
}
selected_date = st.sidebar.selectbox(
    "Date Posted",
    options=list(date_options.keys()),
    index=0
)
st.session_state.filter_date_posted = date_options[selected_date]

# Salary range filter (only if salary data is available)
st.sidebar.markdown("### Salary Range")
col1, col2 = st.sidebar.columns(2)
with col1:
    st.number_input("Min ($)", value=0, step=10000, key="min_salary")
with col2:
    st.number_input("Max ($)", value=1000000, step=10000, key="max_salary")

# Company type filter
company_types = ["Public", "Private", "Nonprofit", "Government", "Startup", "Other"]
st.sidebar.multiselect(
    "Company Type", 
    company_types,
    default=None,
    key="filter_company_types"
)

if st.button("Search Jobs"):
    if search_query:
        with st.spinner('Searching for jobs...'):
            final_query = search_query
            
            # Search for jobs
            job_results = search_jobs(final_query, location)
            
            # Store the results in session state
            st.session_state.job_results = job_results.get('data', [])
            st.session_state.search_completed = True
    else:
        st.warning("Please enter a search query")

# Display Results
if st.session_state.search_completed:
    st.markdown("---")
    st.subheader("Job Search Results")
    
    if st.session_state.job_results:
        # Apply filters
        filtered_jobs = apply_filters(st.session_state.job_results)
        
        if filtered_jobs:
            st.success(f"Found {len(filtered_jobs)} jobs matching your criteria")
            
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
                sort_by_match = st.checkbox("Sort jobs by skill match percentage", value=True)
                if sort_by_match:
                    filtered_jobs = sorted(filtered_jobs, key=lambda x: x.get('match_percentage', 0), reverse=True)
            
            for job_idx, job in enumerate(filtered_jobs):
                # Customize job title based on match percentage if resume uploaded
                if st.session_state.resume_parsed and 'match_percentage' in job:
                    job_title = f"{job_idx+1}. {job.get('job_title', 'Job Title Not Available')} - {job.get('employer_name', 'Company Not Available')} "
                    job_title += f"[Match: {job.get('match_percentage')}%]"
                else:
                    job_title = f"{job_idx+1}. {job.get('job_title', 'Job Title Not Available')} - {job.get('employer_name', 'Company Not Available')}"
                
                with st.expander(job_title):
                    cols = st.columns([2, 1])
                    
                    with cols[0]:
                        # Job details
                        st.write(f"**Company:** {job.get('employer_name', 'Not Available')}")
                        st.write(f"**Location:** {job.get('job_city', 'Not Available')}, {job.get('job_country', 'Not Available')}")
                        st.write(f"**Employment Type:** {job.get('job_employment_type', 'Not Available')}")
                        
                        # Remote information
                        st.write(f"**Remote:** {'Yes' if job.get('job_is_remote') else 'No'}")
                        
                        # Date posted and expiration
                        if job.get('job_posted_at_datetime_utc'):
                            st.write(f"**Posted:** {job.get('job_posted_at_datetime_utc', 'Not Available')}")
                        
                        # Salary information
                        if job.get('job_min_salary') and job.get('job_max_salary'):
                            st.write(f"**Salary Range:** ${job.get('job_min_salary', 'Not Available')} - ${job.get('job_max_salary', 'Not Available')} {job.get('job_salary_currency', 'USD')}")
                    
                    with cols[1]:
                        # Enhanced skills match section
                        if st.session_state.resume_parsed:
                            match_percentage = job.get('match_percentage', 0)
                            matched_skills = job.get('matched_skills', [])
                            
                            # Create a visual progress bar for match percentage
                            st.markdown("### Skills Match")
                            
                            # Color coding based on match percentage
                            if match_percentage > 70:
                                bar_color = "green"
                            elif match_percentage > 40:
                                bar_color = "orange"
                            else:
                                bar_color = "red"
                                
                            # Display progress bar
                            st.progress(match_percentage / 100)
                            st.markdown(f"<h4 style='color:{bar_color};margin-top:0'>{match_percentage}% Match</h4>", unsafe_allow_html=True)
                            
                            if matched_skills:
                                st.markdown("**Matching Skills:**")
                                skill_cols = st.columns(2)
                                for skill_idx, skill in enumerate(matched_skills[:10]):  # Changed variable name from i to skill_idx
                                    col_idx = skill_idx % 2
                                    with skill_cols[col_idx]:
                                        st.markdown(f"✅ {skill}")
                                        
                                if len(matched_skills) > 10:
                                    st.markdown(f"*...and {len(matched_skills)-10} more*")
                            else:
                                st.write("⚠️ No direct skill matches found")
                    
                    # Description
                    st.markdown("**Job Description:**")
                    full_desc = job.get('job_description', 'No description available')
                    
                    if len(full_desc) > 1000:
                        st.markdown(full_desc[:1000] + "...")
                        if st.button(f"Show Full Description for Job {job_idx+1}", key=f"show_desc_{job_idx}"):
                            st.markdown(full_desc)
                    else:
                        st.markdown(full_desc)

                    # Display ALL application links
                    st.markdown("**Apply Links:**")
                    apply_options = job.get('apply_options', [])
                    if apply_options:
                        for option in apply_options:
                            st.markdown(f"[Apply on {option.get('publisher', 'Job Board')}]({option.get('apply_link')})")
                    elif job.get('job_apply_link'):
                        st.markdown(f"[Apply for this job]({job.get('job_apply_link')})")
        else:
            st.info("No jobs match your filters. Try adjusting your filter criteria.")
    else:
        st.info("No jobs found matching your search criteria. Try adjusting your search terms or location.")


st.markdown("---")
st.markdown("### How to use this app")
st.markdown("""
1. Upload your resume in PDF format to extract your skills and experience
2. Enter your job search query and preferred location
3. Review job listings and apply directly to positions you're interested in
""")


# Display app statistics
st.sidebar.markdown("### App Statistics")
if st.session_state.resume_parsed:
    st.sidebar.success("✅ Resume Parsed")
    skill_count = len(st.session_state.parsed_data.get("skills", [])) + len(st.session_state.parsed_data.get("technical_skills", []))
    st.sidebar.metric("Skills Detected", skill_count)
else:
    st.sidebar.warning("❌ No Resume Uploaded")

if st.session_state.search_completed:
    st.sidebar.success("✅ Job Search Completed")
    st.sidebar.metric("Jobs Found", len(st.session_state.job_results))
else:
    st.sidebar.warning("❌ No Search Performed")