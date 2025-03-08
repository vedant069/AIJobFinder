# rag.py
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import google as genai
import os

class SimpleRAG:
    def __init__(self, api_key):
        # Initialize the embedding model and generative AI
        self.embedder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
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
        Process search result data and index it.
        'search_data' should be a list of job posting dictionaries.
        For each job posting, we combine key fields (e.g., job title and description) and then chunk the text.
        """
        try:
            self.processing_status = "Processing search data..."
            combined_text = ""
            for job in search_data:
                # Combine job title and job description (you can add more fields if needed)
                job_title = job.get('job_title', '')
                job_description = job.get('job_description', '')
                combined_text += f"Job Title: {job_title}. Description: {job_description}. "

            if not combined_text.strip():
                raise Exception("No text found in search results.")
            
            # Chunk the combined text
            self.chunks = self.chunk_text(combined_text)
            if not self.chunks:
                raise Exception("No content chunks were generated from search data.")
            
            # Generate embeddings and create the FAISS index
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
        """Return the current processing status."""
        return {
            "is_initialized": self.is_initialized,
            "status": self.processing_status
        }

    def get_relevant_chunks(self, query, k=3):
        """Retrieve the top-k most relevant text chunks for a given query."""
        query_vector = self.embedder.encode([query])
        distances, chunk_indices = self.index.search(query_vector.astype('float32'), k)
        return [self.chunks[i] for i in chunk_indices[0]]

    def query(self, question):
        """Query the RAG system with a user question."""
        if not self.is_initialized:
            raise Exception("RAG system not initialized. Please process search data first.")
        try:
            context = self.get_relevant_chunks(question)
            prompt = f"""
            Based on the following context, provide a clear and concise answer.
            If the context doesn't contain enough relevant information, say "I don't have enough information to answer that question."

            Context:
            {' '.join(context)}

            Question: {question}
            """
            response = self.model.generate_content(prompt)
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
