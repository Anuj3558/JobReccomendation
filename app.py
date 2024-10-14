from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
import re

# Initialize Flask app
app = Flask(__name__)

# MongoDB setup
client = MongoClient(
    "mongodb://anujloharkar3557:3558@cluster0-shard-00-00.putip.mongodb.net:27017,"
    "cluster0-shard-00-01.putip.mongodb.net:27017,"
    "cluster0-shard-00-02.putip.mongodb.net:27017/joblisting?"
    "ssl=true&replicaSet=atlas-6dcgli-shard-0&authSource=admin&retryWrites=true&w=majority&appName=Cluster0"
)
db = client.joblisting

# Function to fetch open jobs from MongoDB
def get_job_data():
    job_collection = db.jobs
    jobs = list(job_collection.find({"status": "Open"}))
    return jobs

# Scoring algorithm for job matching
def calculate_job_score(user, job):
    score = 0

    # Skills match
    user_skills = set(user.get("skills", []))
    job_skills = set(re.findall(r'\b\w+\b', job.get("description", "").lower()))
    skill_match = len(user_skills.intersection(job_skills))
    score += skill_match * 10

    # Experience match
    user_experience = sum(
        [int(re.search(r'\d+', exp.get("duration", "0 months")).group()) 
         for exp in user.get("experience", [])]
    )
    job_experience = int(re.search(r'\d+', job.get("experienceRequirements", ["0"])[0]).group() or 0)
    if user_experience >= job_experience:
        score += 20

    # Education match
    user_education = [edu.get("course", "").lower() for edu in user.get("education", [])]
    job_education = [edu.lower() for edu in job.get("educationRequirements", [])]
    if any(edu in job_education for edu in user_education):
        score += 15

    # Location match
    if user.get("location", "").lower() == job.get("location", "").lower():
        score += 10

    return score

# Function to convert MongoDB objects to JSON serializable format
def serialize_job(job):
    job["_id"] = str(job["_id"])
    return job

# API route for job recommendations
@app.route('/recommend_jobs', methods=['POST'])
def recommend_jobs():
    user_data = request.get_json()
    
    if not user_data:
        return jsonify({"error": "User data is required"}), 400

    try:
        jobs = get_job_data()
        if not jobs:
            return jsonify({"message": "No open jobs found"}), 404

        # Calculate scores for each job
        job_scores = [
            {"job": serialize_job(job), "score": calculate_job_score(user_data, job)}
            for job in jobs
        ]
        job_scores.sort(key=lambda x: x["score"], reverse=True)

        # Return top 5 job recommendations
        top_jobs = job_scores[:5]
        return jsonify(top_jobs), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Run the app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
