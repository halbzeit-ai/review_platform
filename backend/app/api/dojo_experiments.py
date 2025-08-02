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

@router.delete("/cleanup-dojo-projects")
async def cleanup_dojo_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clean up dojo-created projects while preserving all experimental data (PDFs, experiments, results)"""
    try:
        # Check if user is GP
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can cleanup dojo projects"
            )
        
        # Delete project documents first (foreign key constraint)
        # Only delete documents associated with dojo projects, not the original pitch_decks or extraction_experiments
        delete_project_docs_query = text("""
            DELETE FROM project_documents 
            WHERE project_id IN (
                SELECT id FROM projects 
                WHERE is_test = TRUE 
                AND project_metadata::json->>'created_from_experiment' = 'true'
            )
        """)
        
        # Delete dojo projects (created from experiments)
        delete_dojo_projects_query = text("""
            DELETE FROM projects 
            WHERE is_test = TRUE 
            AND project_metadata::json->>'created_from_experiment' = 'true'
        """)
        
        docs_deleted = db.execute(delete_project_docs_query).rowcount
        projects_deleted = db.execute(delete_dojo_projects_query).rowcount
        
        db.commit()
        
        logger.info(f"Cleaned up {projects_deleted} dojo projects and {docs_deleted} associated documents by {current_user.email}")
        
        return {
            "message": f"Cleaned up {projects_deleted} dojo projects and {docs_deleted} associated documents",
            "projects_deleted": projects_deleted,
            "documents_deleted": docs_deleted,
            "experimental_data_preserved": True,
            "note": "All experimental data (experiments, PDFs, results files) have been preserved"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up dojo projects: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup dojo projects"
        )

# ==================== ADD DOJO COMPANIES FUNCTIONALITY ====================

class AddDojoCompaniesRequest(BaseModel):
    experiment_id: int

class AddDojoCompaniesResponse(BaseModel):
    message: str
    experiment_id: int
    companies_added: int
    projects_created: int
    companies_created: List[str]

@router.post("/add-companies", response_model=AddDojoCompaniesResponse)
async def add_dojo_companies_from_experiment(
    request: AddDojoCompaniesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add companies from a dojo experiment to the projects database"""
    try:
        # Check if user is GP
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can add companies from experiments"
            )
        
        # Get the experiment details
        experiment = db.execute(text("""
            SELECT id, experiment_name, extraction_type, text_model_used, 
                   extraction_prompt, created_at, results_json, pitch_deck_ids,
                   classification_enabled, classification_results_json,
                   company_name_results_json, funding_amount_results_json,
                   template_processing_results_json, template_processing_completed_at
            FROM extraction_experiments 
            WHERE id = :experiment_id
        """), {"experiment_id": request.experiment_id}).fetchone()
        
        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Experiment not found"
            )
        
        # Parse experiment data
        results_data = json.loads(experiment[6]) if experiment[6] else {}
        classification_data = json.loads(experiment[9]) if experiment[9] else {}
        company_name_data = json.loads(experiment[10]) if experiment[10] else {}
        funding_amount_data = json.loads(experiment[11]) if experiment[11] else {}
        template_processing_data = json.loads(experiment[12]) if experiment[12] else {}
        
        # Check if experiment has required data
        if not experiment[8]:  # classification_enabled
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Experiment does not have classification data"
            )
        
        if not results_data.get("results"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Experiment has no extraction results"
            )
        
        # Extract results and prepare for processing
        results = results_data.get("results", [])
        classification_lookup = {}
        company_name_lookup = {}
        funding_amount_lookup = {}
        template_processing_lookup = {}
        
        # Build lookups for classification and company name data
        if classification_data.get("classification_by_deck"):
            classification_lookup = classification_data["classification_by_deck"]
            logger.info(f"Classification lookup keys: {list(classification_lookup.keys())}")
        
        if company_name_data.get("company_name_results"):
            for result in company_name_data["company_name_results"]:
                company_name_lookup[result.get("deck_id")] = result.get("company_name")
        
        # Build funding amount lookup
        if funding_amount_data.get("funding_amount_results"):
            for result in funding_amount_data["funding_amount_results"]:
                funding_amount_lookup[result.get("deck_id")] = result.get("funding_amount")
            logger.info(f"Funding amount lookup keys: {list(funding_amount_lookup.keys())}")
        
        # Build template processing lookup
        if template_processing_data.get("template_processing_results"):
            for result in template_processing_data["template_processing_results"]:
                deck_id = result.get("deck_id")
                if deck_id:
                    template_processing_lookup[deck_id] = {
                        "template_analysis": result.get("template_analysis"),
                        "template_used": result.get("template_used"),
                        "thumbnail_path": result.get("thumbnail_path"),
                        "slide_images": result.get("slide_images", [])
                    }
            logger.info(f"Template processing lookup keys: {list(template_processing_lookup.keys())}")
        
        # Process each result to create companies/projects
        companies_added = 0
        projects_created = 0
        companies_created = []
        
        for result in results:
            deck_id = result.get("deck_id")
            offering_extraction = result.get("offering_extraction", "")
            funding_extraction = result.get("funding_extraction", "")
            
            # Skip failed extractions
            if not offering_extraction or offering_extraction.startswith("Error:"):
                continue
            
            # Get company name (prioritize AI extracted name, fallback to deck filename)
            company_name = None
            if deck_id in company_name_lookup:
                company_name = company_name_lookup[deck_id]
            elif result.get("ai_extracted_startup_name"):
                company_name = result["ai_extracted_startup_name"]
            elif result.get("filename"):
                # Extract company name from filename as fallback
                filename = result["filename"]
                if filename.endswith(".pdf"):
                    filename = filename[:-4]
                company_name = filename.replace("_", " ").replace("-", " ").title()
            
            if not company_name:
                logger.warning(f"No company name found for deck {deck_id}, skipping")
                continue
            
            # Generate company_id from company name
            company_id = get_company_id_from_name(company_name)
            
            # Check if this deck from this experiment was already processed
            duplicate_check = text("""
                SELECT id FROM projects 
                WHERE project_metadata::json->>'experiment_id' = :experiment_id 
                AND project_metadata::json->>'source_deck_id' = :deck_id
            """)
            existing_project = db.execute(duplicate_check, {
                "experiment_id": str(request.experiment_id),
                "deck_id": str(deck_id)
            }).fetchone()
            
            if existing_project:
                logger.info(f"Skipping deck {deck_id} - already processed from experiment {request.experiment_id}")
                continue
            
            # Ensure unique company_id
            existing_check = text("SELECT id FROM projects WHERE company_id = :company_id LIMIT 1")
            if db.execute(existing_check, {"company_id": company_id}).fetchone():
                company_id = f"{company_id}-dojo-{uuid.uuid4().hex[:6]}"
            
            # Get classification data for this deck
            classification_info = classification_lookup.get(str(deck_id), {})
            
            # If no classification found by deck_id, try to extract from result directly
            if not classification_info and result.get("classification"):
                classification_info = {"primary_sector": result.get("classification")}
            
            primary_sector = classification_info.get("primary_sector") or "Digital Health"
            
            logger.info(f"Deck {deck_id}: classification='{primary_sector}'")
            
            # Create project name
            project_name = f"{company_name} - Dojo Analysis"
            
            # Create project entry
            project_insert = text("""
                INSERT INTO projects (
                    company_id, project_name, funding_round, funding_sought, 
                    company_offering, tags, is_test, is_active, project_metadata, 
                    created_at, updated_at
                )
                VALUES (:company_id, :project_name, :funding_round, :funding_sought,
                        :company_offering, :tags, TRUE, TRUE, :metadata, 
                        :created_at, :updated_at)
                RETURNING id
            """)
            
            # Generate metadata
            metadata = {
                "created_from_experiment": True,
                "experiment_id": request.experiment_id,
                "experiment_name": experiment[1],
                "source_deck_id": deck_id,
                "created_by": current_user.email,
                "created_at": datetime.utcnow().isoformat(),
                "original_filename": result.get("filename"),
                "classification": classification_info,
                "ai_extracted_company_name": company_name_lookup.get(deck_id),
                "template_processing": template_processing_lookup.get(deck_id)
            }
            
            # Get funding from the lookup (if available) or fallback to funding_extraction
            funding_sought_value = funding_amount_lookup.get(deck_id) or funding_extraction or "TBD"
            
            logger.info(f"Deck {deck_id}: funding='{funding_sought_value}'")
            
            project_result = db.execute(project_insert, {
                "company_id": company_id,
                "project_name": project_name,
                "funding_round": "analysis",
                "funding_sought": funding_sought_value,
                "company_offering": offering_extraction[:2000],  # Limit to 2000 chars
                "tags": json.dumps(["dojo", "experiment", "ai-extracted", (primary_sector or "digital-health").lower().replace(" ", "-")]),
                "metadata": json.dumps(metadata),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            
            project_id = project_result.fetchone()[0]
            projects_created += 1
            companies_created.append(company_name)
            
            # Add pitch deck as project document
            pitch_deck_query = text("""
                SELECT id, file_name, file_path, results_file_path
                FROM pitch_decks 
                WHERE id = :deck_id
            """)
            pitch_deck_info = db.execute(pitch_deck_query, {"deck_id": deck_id}).fetchone()
            
            if pitch_deck_info:
                # Add pitch deck document
                deck_doc_insert = text("""
                    INSERT INTO project_documents (
                        project_id, document_type, file_name, file_path,
                        original_filename, processing_status, uploaded_by,
                        upload_date, is_active
                    )
                    VALUES (:project_id, 'pitch_deck', :file_name, :file_path,
                            :original_filename, 'completed', :uploaded_by,
                            :upload_date, TRUE)
                    RETURNING id
                """)
                
                deck_doc_result = db.execute(deck_doc_insert, {
                    "project_id": project_id,
                    "file_name": pitch_deck_info[1],  # file_name
                    "file_path": pitch_deck_info[2],  # file_path
                    "original_filename": pitch_deck_info[1],
                    "uploaded_by": current_user.id,
                    "upload_date": datetime.utcnow()
                })
                
                deck_document_id = deck_doc_result.fetchone()[0]
                logger.info(f"Added pitch deck document {deck_document_id} to project {project_id}")
                
                # Add results file if it exists
                if pitch_deck_info[3]:  # results_file_path
                    results_doc_insert = text("""
                        INSERT INTO project_documents (
                            project_id, document_type, file_name, file_path,
                            original_filename, processing_status, uploaded_by,
                            upload_date, is_active
                        )
                        VALUES (:project_id, 'analysis_results', :file_name, :file_path,
                                :original_filename, 'completed', :uploaded_by,
                                :upload_date, TRUE)
                    """)
                    
                    results_filename = f"{company_name}_analysis_results.json"
                    db.execute(results_doc_insert, {
                        "project_id": project_id,
                        "file_name": results_filename,
                        "file_path": pitch_deck_info[3],  # results_file_path
                        "original_filename": results_filename,
                        "uploaded_by": current_user.id,
                        "upload_date": datetime.utcnow()
                    })
                    
                    logger.info(f"Added results document to project {project_id}")
            
            logger.info(f"Created project for {company_name} (company_id: {company_id}, project_id: {project_id})")
        
        companies_added = len(set(companies_created))  # Count unique companies
        
        db.commit()
        
        logger.info(f"Summary: Added {companies_added} companies from experiment {request.experiment_id} ({len(results)} processed)")
        
        logger.info(f"Added {companies_added} companies from experiment {request.experiment_id} by {current_user.email}")
        
        return AddDojoCompaniesResponse(
            message=f"Successfully added {companies_added} companies and created {projects_created} projects from experiment",
            experiment_id=request.experiment_id,
            companies_added=companies_added,
            projects_created=projects_created,
            companies_created=list(set(companies_created))  # Return unique company names
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding companies from experiment {request.experiment_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add companies from experiment"
        )