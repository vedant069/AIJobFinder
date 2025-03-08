import streamlit as st
import http.client
import json
import os
import PyPDF2
import io
import requests
import time
from google import genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ----------------------------
# RAG Chatbot Implementation
# ----------------------------
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

class SimpleRAG:
    def __init__(self, api_key):
        # Initialize the embedding model and generative AI client
        self.embedder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.0-flash"
        self.index = None
        self.chunks = []
        self.is_initialized = False
        self.processing_status = None

    def chunk_text(self, text, chunk_size=700):
        """Split text into smaller chunks."""
        words = text.split()
        return [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

    def process_search_data(self, search_data):
        """
        Process job search result data and index it.
        For each job posting, extract only the 'job_title' and 'job_description' fields.
        """
        try:
            self.processing_status = "Processing job search data..."
            job_docs = []
            for job in search_data:
                title = job.get('job_title', '')
                description = job.get('job_description', '')
                # Create a document string with only job title and description.
                doc = f"Job Title: {title}. Job Description: {description}."
                job_docs.append(doc)
            # Join each job document with a delimiter.
            combined_text = " ||| ".join(job_docs)
            if not combined_text.strip():
                raise Exception("No text found in job search results.")
            self.chunks = self.chunk_text(combined_text)
            if not self.chunks:
                raise Exception("No content chunks were generated from job data.")
            embeddings = self.embedder.encode(self.chunks)
            vector_dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(vector_dimension)
            self.index.add(np.array(embeddings).astype('float32'))
            self.is_initialized = True
            self.processing_status = f"RAG system initialized with {len(self.chunks)} chunks."
            return {"status": "success", "message": self.processing_status}
        except Exception as e:
            self.processing_status = f"Error: {str(e)}"
            self.is_initialized = False
            return {"status": "error", "message": str(e)}

    def get_status(self):
        """Return current processing status."""
        return {
            "is_initialized": self.is_initialized,
            "status": self.processing_status
        }

    def get_relevant_chunks(self, query, k=3):
        """Retrieve top-k relevant text chunks for a query."""
        query_vector = self.embedder.encode([query])
        distances, chunk_indices = self.index.search(query_vector.astype('float32'), k)
        return [self.chunks[i] for i in chunk_indices[0]]

    def query(self, question):
        """Query the RAG system with a question."""
        if not self.is_initialized:
            raise Exception("RAG system not initialized. Please process job data first.")
        try:
            context = self.get_relevant_chunks(question)
            prompt = f"""
            Based on the following context, provide a clear and concise answer.
            If the context doesn't contain enough relevant information, say "I don't have enough information to answer that question."

            Context:
            {' '.join(context)}

            Question: {question}
            """
            response = self.client.models.generate_content(model=self.model, contents=prompt)
            return {
                "status": "success",
                "answer": response.text.strip(),
                "context": context
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

# ----------------------------
# Main Job Search Engine Code
# ----------------------------
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
    /* Chatbot styling */
    .chat-box {
        background-color: #F8F9FA;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .user-message {
        color: #0D6EFD;
        font-weight: bold;
    }
    .bot-message {
        color: #198754;
        font-weight: bold;
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
        client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        prompt = f"""
        Parse the following resume text and extract information according to this exact JSON schema:
        
        {json.dumps(RESUME_SCHEMA, indent=2)}
        
        Resume text:
        {resume_text}
        
        Make sure to follow the schema exactly. If any information is not available, use empty strings or empty arrays as appropriate.
        Return ONLY the JSON object with no additional text.
        """
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        try:
            parsed_data = json.loads(response.text)
            return parsed_data
        except json.JSONDecodeError:
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
        if st.session_state.filter_remote_only and not job.get('job_is_remote', False):
            continue
        if st.session_state.filter_employment_types and job.get('job_employment_type') not in st.session_state.filter_employment_types:
            continue
        if st.session_state.filter_date_posted > 0:
            current_time = int(time.time())
            posted_time = job.get('job_posted_at_timestamp', 0)
            days_ago = (current_time - posted_time) / (60 * 60 * 24)
            if days_ago > st.session_state.filter_date_posted:
                continue
        if job.get('job_min_salary') is not None and job.get('job_min_salary') < st.session_state.min_salary:
            continue
        if job.get('job_max_salary') is not None and job.get('job_max_salary') > st.session_state.max_salary:
            continue
        if st.session_state.filter_company_types and job.get('employer_company_type') not in st.session_state.filter_company_types:
            continue
        filtered_jobs.append(job)
    return filtered_jobs

# ----------------------------
# Step 1: Resume Upload Section
# ----------------------------
st.subheader("Step 1: Upload Your Resume First")
uploaded_file = st.file_uploader("Upload your resume (PDF format)", type=['pdf'])
if uploaded_file is not None:
    with st.spinner('Processing your resume...'):
        resume_text = extract_text_from_pdf(uploaded_file)
        st.session_state.resume_text = resume_text
        parsed_data = parse_resume_with_gemini(resume_text)
        st.session_state.parsed_data = parsed_data
        st.session_state.resume_parsed = True
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
                st.write("**Technical Skills:**")
                tech_skills = parsed_data.get("technical_skills", [])
                st.write(", ".join(tech_skills) if tech_skills else "No technical skills found")
                st.write("**Soft Skills:**")
                soft_skills = parsed_data.get("soft_skills", [])
                st.write(", ".join(soft_skills) if soft_skills else "No soft skills found")
                st.write("**General Skills:**")
                skills = parsed_data.get("skills", [])
                st.write(", ".join(skills) if skills else "No general skills found")
                st.markdown("### Education")
                for edu in parsed_data.get("education", []):
                    st.write(f"**{edu.get('degree', 'Degree')}** - {edu.get('institution', 'Institution')}")
                    st.write(f"*{edu.get('year', 'Year not specified')}*")
                st.write(f"**Years of Experience:** {parsed_data.get('years_of_experience', 'Not specified')}")

st.markdown("---")
# ----------------------------
# Step 2: Job Search Section
# ----------------------------
st.subheader("Step 2: Search for Jobs")
search_query = st.text_input("Enter your job search query (e.g., 'Python Developer')")
location = st.text_input("Location (e.g., 'New York', 'Remote')")
st.sidebar.markdown("### Filter Options")
st.sidebar.checkbox("Remote Only", key="filter_remote_only")
employment_types = ["FULLTIME", "PARTTIME", "CONTRACTOR", "INTERN"]
st.sidebar.multiselect("Employment Type", employment_types, default=None, key="filter_employment_types")
date_options = {"Any time": 0, "Past 24 hours": 1, "Past week": 7, "Past month": 30}
selected_date = st.sidebar.selectbox("Date Posted", options=list(date_options.keys()), index=0)
st.session_state.filter_date_posted = date_options[selected_date]
st.sidebar.markdown("### Salary Range")
col1, col2 = st.sidebar.columns(2)
with col1:
    st.number_input("Min ($)", value=0, step=10000, key="min_salary")
with col2:
    st.number_input("Max ($)", value=1000000, step=10000, key="max_salary")
company_types = ["Public", "Private", "Nonprofit", "Government", "Startup", "Other"]
st.sidebar.multiselect("Company Type", company_types, default=None, key="filter_company_types")

if st.button("Search Jobs"):
    if search_query:
        with st.spinner('Searching for jobs...'):
            final_query = search_query
            job_results = search_jobs(final_query, location)
            st.session_state.job_results = job_results.get('data', [])
            st.session_state.search_completed = True
    else:
        st.warning("Please enter a search query")

# Display Job Search Results
if st.session_state.search_completed:
    st.markdown("---")
    st.subheader("Job Search Results")
    if st.session_state.job_results:
        filtered_jobs = apply_filters(st.session_state.job_results)
        if filtered_jobs:
            st.success(f"Found {len(filtered_jobs)} jobs matching your criteria")
            if st.session_state.resume_parsed:
                tech_skills = set(st.session_state.parsed_data.get("technical_skills", []))
                general_skills = set(st.session_state.parsed_data.get("skills", []))
                soft_skills = set(st.session_state.parsed_data.get("soft_skills", []))
                all_skills = tech_skills.union(general_skills).union(soft_skills)
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
                sort_by_match = st.checkbox("Sort jobs by skill match percentage", value=True)
                if sort_by_match:
                    filtered_jobs = sorted(filtered_jobs, key=lambda x: x.get('match_percentage', 0), reverse=True)
            for job_idx, job in enumerate(filtered_jobs):
                if st.session_state.resume_parsed and 'match_percentage' in job:
                    job_title = f"{job_idx+1}. {job.get('job_title', 'Job Title Not Available')} - {job.get('employer_name', 'Company Not Available')} [Match: {job.get('match_percentage')}%]"
                else:
                    job_title = f"{job_idx+1}. {job.get('job_title', 'Job Title Not Available')} - {job.get('employer_name', 'Company Not Available')}"
                with st.expander(job_title):
                    cols = st.columns([2, 1])
                    with cols[0]:
                        st.write(f"**Company:** {job.get('employer_name', 'Not Available')}")
                        st.write(f"**Location:** {job.get('job_city', 'Not Available')}, {job.get('job_country', 'Not Available')}")
                        st.write(f"**Employment Type:** {job.get('job_employment_type', 'Not Available')}")
                        st.write(f"**Remote:** {'Yes' if job.get('job_is_remote') else 'No'}")
                        if job.get('job_posted_at_datetime_utc'):
                            st.write(f"**Posted:** {job.get('job_posted_at_datetime_utc', 'Not Available')}")
                        if job.get('job_min_salary') and job.get('job_max_salary'):
                            st.write(f"**Salary Range:** ${job.get('job_min_salary', 'Not Available')} - ${job.get('job_max_salary', 'Not Available')} {job.get('job_salary_currency', 'USD')}")
                    with cols[1]:
                        if st.session_state.resume_parsed:
                            match_percentage = job.get('match_percentage', 0)
                            matched_skills = job.get('matched_skills', [])
                            st.markdown("### Skills Match")
                            bar_color = "green" if match_percentage > 70 else "orange" if match_percentage > 40 else "red"
                            st.progress(match_percentage / 100)
                            st.markdown(f"<h4 style='color:{bar_color};margin-top:0'>{match_percentage}% Match</h4>", unsafe_allow_html=True)
                            if matched_skills:
                                st.markdown("**Matching Skills:**")
                                skill_cols = st.columns(2)
                                for skill_idx, skill in enumerate(matched_skills[:10]):
                                    col_idx = skill_idx % 2
                                    with skill_cols[col_idx]:
                                        st.markdown(f"✅ {skill}")
                                if len(matched_skills) > 10:
                                    st.markdown(f"*...and {len(matched_skills)-10} more*")
                            else:
                                st.write("⚠️ No direct skill matches found")
                    st.markdown("**Job Description:**")
                    full_desc = job.get('job_description', 'No description available')
                    if len(full_desc) > 1000:
                        st.markdown(full_desc[:1000] + "...")
                        if st.button(f"Show Full Description for Job {job_idx+1}", key=f"show_desc_{job_idx}"):
                            st.markdown(full_desc)
                    else:
                        st.markdown(full_desc)
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

# ----------------------------
# Step 3: RAG Chatbot Interface
# ----------------------------
st.markdown("---")
st.subheader("Chat with Job Data (RAG Chatbot)")

# Initialize RAG session state variables
if 'rag_system' not in st.session_state:
    API_KEY = 'AIzaSyAOK9vRTSRQzd22B2gmbiuIePbZTDyaGYs'
    st.session_state.rag_system = SimpleRAG(api_key=API_KEY)
if 'rag_initialized' not in st.session_state:
    st.session_state.rag_initialized = False
if 'rag_chat_history' not in st.session_state:
    st.session_state.rag_chat_history = []

# Button to load job search data into the RAG system
if st.button("Load Job Data into Chatbot"):
    if st.session_state.job_results:
        with st.spinner("Processing job data for chatbot..."):
            result = st.session_state.rag_system.process_search_data(st.session_state.job_results)
            if result['status'] == 'success':
                st.success(result['message'])
                st.session_state.rag_initialized = True
            else:
                st.error(result['message'])
    else:
        st.warning("No job data available. Please perform a job search first.")

# Chat input form
with st.form("rag_chat_form", clear_on_submit=True):
    user_question = st.text_input("Ask a question about the job data")
    submit_chat = st.form_submit_button("Send")

if submit_chat and user_question:
    if st.session_state.rag_initialized:
        st.session_state.rag_chat_history.append({"user": user_question})
        with st.spinner("Querying chatbot..."):
            result = st.session_state.rag_system.query(user_question)
        if result["status"] == "success":
            bot_answer = result["answer"]
            st.session_state.rag_chat_history.append({"bot": bot_answer})
        else:
            st.session_state.rag_chat_history.append({"bot": "Error: " + result.get("message", "Unknown error")})
    else:
        st.error("RAG system not initialized. Please load job data into the chatbot first.")

# Display chat history
st.markdown('<div class="chat-box">', unsafe_allow_html=True)
for msg in st.session_state.rag_chat_history:
    if "user" in msg:
        st.markdown(f"<p class='user-message'>User: {msg['user']}</p>", unsafe_allow_html=True)
    elif "bot" in msg:
        st.markdown(f"<p class='bot-message'>Bot: {msg['bot']}</p>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
