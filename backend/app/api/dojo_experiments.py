"""
Dojo Experiments API Endpoints
Handles creation of fake companies and projects for testing project management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import json
import logging
import random
import uuid

from ..db.database import get_db
from ..db.models import User
from .auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dojo-experiments", tags=["dojo-experiments"])

# Pydantic models
class CreateFakeCompaniesRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=200, description="Number of fake companies to create")
    projects_per_company: int = Field(default=1, ge=1, le=5, description="Number of projects per company")
    include_documents: bool = Field(default=False, description="Create fake documents for projects")

class FakeCompanyResponse(BaseModel):
    company_id: str
    company_name: str
    projects_created: int
    documents_created: int

class ExperimentStatsResponse(BaseModel):
    total_test_projects: int
    total_test_documents: int
    total_test_companies: int
    dojo_projects: int
    fake_companies: int

# Sample data for generating fake companies
FAKE_COMPANY_NAMES = [
    "MedTech Innovations", "HealthCore Solutions", "BioVision Systems", "CarePlus Technologies",
    "Digital Health Labs", "SmartMed Analytics", "WellnessTech Co", "LifeScience Partners",
    "HealthFlow Dynamics", "MedConnect Platform", "VitalSign Systems", "CureWave Technologies",
    "HealthBridge Solutions", "MedAdvance Group", "LifeTech Innovations", "HealthSphere Systems",
    "BioMetrics Plus", "CareSync Technologies", "HealthGuard Solutions", "MedFuture Labs",
    "VitalCare Systems", "HealthTech Pioneers", "BioConnect Solutions", "MedStream Analytics",
    "LifeBalance Technologies", "HealthPulse Systems", "CareTech Innovations", "MedVision Pro",
    "HealthLink Solutions", "BioFlow Systems", "VitalTech Partners", "MedSmart Solutions",
    "HealthCore Analytics", "LifeTech Systems", "CareFlow Technologies", "MedAdvantage Labs",
    "HealthSync Solutions", "BioTech Innovations", "VitalFlow Systems", "MedConnect Labs",
    "HealthPro Technologies", "LifeStream Solutions", "CareTech Analytics", "MedFlow Systems",
    "HealthTech Solutions", "BioVital Labs", "VitalCare Technologies", "MedBridge Systems",
    "HealthLink Analytics", "LifeTech Pro", "CareConnect Solutions", "MedVision Systems"
]

FUNDING_ROUNDS = ["pre_seed", "seed", "series_a", "series_b", "series_c", "bridge"]
HEALTHCARE_SECTORS = ["Digital Health", "Medical Devices", "Biotechnology", "Pharmaceuticals", "Health Analytics", "Telemedicine"]
COMPANY_OFFERINGS = [
    "AI-powered diagnostic platform for early disease detection",
    "Wearable health monitoring devices with real-time analytics",
    "Telemedicine platform connecting patients with specialists",
    "Drug discovery platform using machine learning algorithms",
    "Digital therapeutics for mental health and wellness",
    "Medical imaging analysis software with AI enhancement",
    "Electronic health records optimization system",
    "Remote patient monitoring for chronic disease management",
    "Precision medicine platform for personalized treatments",
    "Healthcare data analytics and insights platform"
]

def get_company_id_from_name(company_name: str) -> str:
    """Generate company_id from company name"""
    import re
    return re.sub(r'[^a-z0-9-]', '', re.sub(r'\s+', '-', company_name.lower()))

@router.get("/stats", response_model=ExperimentStatsResponse)
async def get_experiment_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get statistics about test/experimental data"""
    try:
        # Check if user is GP
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can access experiment statistics"
            )
        
        # Get test project statistics
        stats_query = text("""
        SELECT 
            COUNT(*) as total_test_projects,
            COUNT(DISTINCT company_id) as total_test_companies,
            SUM(CASE WHEN company_id = 'dojo' THEN 1 ELSE 0 END) as dojo_projects,
            SUM(CASE WHEN company_id != 'dojo' THEN 1 ELSE 0 END) as fake_companies
        FROM projects
        WHERE is_test = TRUE
        """)
        
        result = db.execute(stats_query).fetchone()
        
        # Get document count
        doc_count_query = text("""
        SELECT COUNT(*)
        FROM project_documents pd
        JOIN projects p ON pd.project_id = p.id
        WHERE p.is_test = TRUE
        """)
        
        doc_count = db.execute(doc_count_query).fetchone()[0]
        
        return ExperimentStatsResponse(
            total_test_projects=result[0] or 0,
            total_test_documents=doc_count or 0,
            total_test_companies=result[1] or 0,
            dojo_projects=result[2] or 0,
            fake_companies=result[3] or 0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting experiment stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve experiment statistics"
        )

@router.post("/create-fake-companies", response_model=List[FakeCompanyResponse])
async def create_fake_companies(
    request: CreateFakeCompaniesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create fake companies and projects for testing"""
    try:
        # Check if user is GP
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can create fake companies"
            )
        
        created_companies = []
        
        for i in range(request.count):
            # Generate unique company name
            base_name = random.choice(FAKE_COMPANY_NAMES)
            company_name = f"{base_name} {random.randint(100, 999)}"
            company_id = get_company_id_from_name(company_name)
            
            # Ensure unique company_id
            existing_check = text("SELECT id FROM projects WHERE company_id = :company_id LIMIT 1")
            if db.execute(existing_check, {"company_id": company_id}).fetchone():
                company_id = f"{company_id}-{uuid.uuid4().hex[:6]}"
            
            projects_created = 0
            documents_created = 0
            
            # Create projects for this company
            for j in range(request.projects_per_company):
                funding_round = random.choice(FUNDING_ROUNDS)
                project_name = f"{company_name} - {funding_round.replace('_', ' ').title()} Round"
                
                # Create project
                project_insert = text("""
                INSERT INTO projects (
                    company_id, project_name, funding_round, funding_sought, 
                    company_offering, tags, is_test, project_metadata, 
                    created_at, updated_at
                )
                VALUES (:company_id, :project_name, :funding_round, :funding_sought,
                        :company_offering, :tags, TRUE, :metadata, 
                        :created_at, :updated_at)
                RETURNING id
                """)
                
                # Generate realistic data
                funding_amount = f"€{random.randint(500, 50000)}K"
                company_offering = random.choice(COMPANY_OFFERINGS)
                created_time = datetime.utcnow() - timedelta(days=random.randint(1, 365))
                
                project_result = db.execute(project_insert, {
                    "company_id": company_id,
                    "project_name": project_name,
                    "funding_round": funding_round,
                    "funding_sought": funding_amount,
                    "company_offering": company_offering,
                    "tags": json.dumps(["fake", "experiment", "testing", funding_round]),
                    "metadata": json.dumps({
                        "created_by_experiment": True,
                        "created_by": current_user.email,
                        "experiment_batch": datetime.utcnow().isoformat(),
                        "fake_company_name": company_name
                    }),
                    "created_at": created_time,
                    "updated_at": created_time
                })
                
                project_id = project_result.fetchone()[0]
                projects_created += 1
                
                # Create fake documents if requested
                if request.include_documents:
                    doc_count = random.randint(1, 3)
                    for k in range(doc_count):
                        doc_insert = text("""
                        INSERT INTO project_documents (
                            project_id, document_type, file_name, file_path,
                            original_filename, processing_status, uploaded_by,
                            upload_date, is_active
                        )
                        VALUES (:project_id, :doc_type, :file_name, :file_path,
                                :original_filename, 'completed', :uploaded_by,
                                :upload_date, TRUE)
                        """)
                        
                        doc_types = ["pitch_deck", "financial_report", "market_analysis"]
                        doc_type = random.choice(doc_types)
                        file_name = f"{company_name}_{doc_type}_{k+1}.pdf"
                        file_path = f"fake_documents/{company_id}/{project_id}/{file_name}"
                        
                        db.execute(doc_insert, {
                            "project_id": project_id,
                            "doc_type": doc_type,
                            "file_name": file_name,
                            "file_path": file_path,
                            "original_filename": file_name,
                            "uploaded_by": current_user.id,
                            "upload_date": created_time + timedelta(hours=random.randint(1, 48))
                        })
                        
                        documents_created += 1
            
            created_companies.append(FakeCompanyResponse(
                company_id=company_id,
                company_name=company_name,
                projects_created=projects_created,
                documents_created=documents_created
            ))
        
        db.commit()
        
        logger.info(f"Created {len(created_companies)} fake companies with {sum(c.projects_created for c in created_companies)} projects by {current_user.email}")
        
        return created_companies
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating fake companies: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create fake companies"
        )

@router.delete("/cleanup-test-data")
async def cleanup_test_data(
    keep_dojo: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clean up all test data (optionally keep dojo data)"""
    try:
        # Check if user is GP
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can cleanup test data"
            )
        
        # Delete documents first (foreign key constraint)
        if keep_dojo:
            delete_docs_query = text("""
            DELETE FROM project_documents 
            WHERE project_id IN (
                SELECT id FROM projects 
                WHERE is_test = TRUE AND company_id != 'dojo'
            )
            """)
            
            delete_projects_query = text("""
            DELETE FROM projects 
            WHERE is_test = TRUE AND company_id != 'dojo'
            """)
        else:
            delete_docs_query = text("""
            DELETE FROM project_documents 
            WHERE project_id IN (
                SELECT id FROM projects WHERE is_test = TRUE
            )
            """)
            
            delete_projects_query = text("DELETE FROM projects WHERE is_test = TRUE")
        
        docs_deleted = db.execute(delete_docs_query).rowcount
        projects_deleted = db.execute(delete_projects_query).rowcount
        
        db.commit()
        
        logger.info(f"Cleaned up {projects_deleted} test projects and {docs_deleted} test documents by {current_user.email}")
        
        return {
            "message": f"Cleaned up {projects_deleted} test projects and {docs_deleted} test documents",
            "dojo_data_preserved": keep_dojo
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up test data: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup test data"
        )