--
-- PostgreSQL database dump
--

-- Dumped from database version 16.9 (Ubuntu 16.9-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.9 (Ubuntu 16.9-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: auto_initialize_project_stages(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.auto_initialize_project_stages() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Only initialize stages for new projects that don't have test data
    IF NEW.is_test = FALSE OR NEW.is_test IS NULL THEN
        PERFORM initialize_project_stages(NEW.id);
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: initialize_project_stages(integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.initialize_project_stages(project_id_param integer) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    stage_count INTEGER := 0;
    template_record RECORD;
BEGIN
    -- Insert stages from active templates
    FOR template_record IN 
        SELECT id, stage_name, stage_code, stage_order, estimated_duration_days, stage_metadata
        FROM stage_templates 
        WHERE is_active = TRUE 
        ORDER BY stage_order
    LOOP
        INSERT INTO project_stages (
            project_id, 
            stage_template_id,
            stage_name, 
            stage_code,
            stage_order, 
            status, 
            stage_metadata,
            created_at
        ) VALUES (
            project_id_param,
            template_record.id,
            template_record.stage_name,
            template_record.stage_code,
            template_record.stage_order,
            CASE WHEN template_record.stage_order = 1 THEN 'active' ELSE 'pending' END,
            template_record.stage_metadata,
            CURRENT_TIMESTAMP
        );
        
        stage_count := stage_count + 1;
    END LOOP;
    
    RETURN stage_count;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: analysis_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.analysis_templates (
    id integer NOT NULL,
    healthcare_sector_id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    template_version character varying(50) DEFAULT '1.0'::character varying,
    specialized_analysis text,
    is_active boolean DEFAULT true,
    is_default boolean DEFAULT false,
    usage_count integer DEFAULT 0,
    created_by character varying(255),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    modified_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: analysis_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.analysis_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: analysis_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.analysis_templates_id_seq OWNED BY public.analysis_templates.id;


--
-- Name: answers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.answers (
    id integer NOT NULL,
    question_id integer,
    answer_text text,
    answered_by integer,
    created_at timestamp without time zone
);


--
-- Name: answers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.answers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: answers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.answers_id_seq OWNED BY public.answers.id;


--
-- Name: chapter_analysis_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chapter_analysis_results (
    id integer NOT NULL,
    pitch_deck_id integer NOT NULL,
    chapter_id integer NOT NULL,
    chapter_response text,
    average_score real,
    weighted_score real,
    total_questions integer,
    answered_questions integer,
    processing_time real,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: chapter_analysis_results_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.chapter_analysis_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: chapter_analysis_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.chapter_analysis_results_id_seq OWNED BY public.chapter_analysis_results.id;


--
-- Name: chapter_questions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chapter_questions (
    id integer NOT NULL,
    chapter_id integer NOT NULL,
    question_id character varying(100) NOT NULL,
    question_text text NOT NULL,
    weight real DEFAULT 1.0,
    order_index integer DEFAULT 0,
    enabled boolean DEFAULT true,
    scoring_criteria text,
    healthcare_focus text,
    question_prompt_template text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    modified_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: chapter_questions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.chapter_questions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: chapter_questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.chapter_questions_id_seq OWNED BY public.chapter_questions.id;


--
-- Name: classification_performance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.classification_performance (
    id integer NOT NULL,
    classification_id integer NOT NULL,
    was_accurate boolean,
    manual_correction_from character varying(255),
    manual_correction_to character varying(255),
    correction_reason text,
    corrected_by character varying(255),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: classification_performance_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.classification_performance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: classification_performance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.classification_performance_id_seq OWNED BY public.classification_performance.id;


--
-- Name: extraction_experiments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extraction_experiments (
    id integer NOT NULL,
    experiment_name character varying(255) NOT NULL,
    pitch_deck_ids integer[] NOT NULL,
    extraction_type character varying(50) DEFAULT 'company_offering'::character varying NOT NULL,
    text_model_used character varying(255) NOT NULL,
    extraction_prompt text NOT NULL,
    results_json text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    classification_enabled boolean DEFAULT false,
    classification_results_json text,
    classification_model_used character varying(255) DEFAULT NULL::character varying,
    classification_prompt_used text,
    classification_completed_at timestamp without time zone,
    company_name_results_json text,
    company_name_completed_at timestamp without time zone,
    funding_amount_results_json text,
    funding_amount_completed_at timestamp without time zone,
    deck_date_results_json text,
    deck_date_completed_at timestamp without time zone,
    template_processing_results_json text,
    template_processing_completed_at timestamp without time zone
);


--
-- Name: TABLE extraction_experiments; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.extraction_experiments IS 'Tracks extraction experiments for comparing different models and prompts';


--
-- Name: COLUMN extraction_experiments.pitch_deck_ids; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.extraction_experiments.pitch_deck_ids IS 'Array of pitch_deck IDs included in this experiment';


--
-- Name: COLUMN extraction_experiments.extraction_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.extraction_experiments.extraction_type IS 'Type of extraction being tested (company_offering, etc.)';


--
-- Name: COLUMN extraction_experiments.results_json; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.extraction_experiments.results_json IS 'JSON object containing extraction results for each deck in sample';


--
-- Name: COLUMN extraction_experiments.classification_enabled; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.extraction_experiments.classification_enabled IS 'Whether classification enrichment has been requested for this experiment';


--
-- Name: COLUMN extraction_experiments.classification_results_json; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.extraction_experiments.classification_results_json IS 'JSON object containing classification results for each deck in the experiment';


--
-- Name: COLUMN extraction_experiments.classification_model_used; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.extraction_experiments.classification_model_used IS 'Model used for classification (if different from text model)';


--
-- Name: COLUMN extraction_experiments.classification_prompt_used; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.extraction_experiments.classification_prompt_used IS 'Prompt used for classification';


--
-- Name: COLUMN extraction_experiments.classification_completed_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.extraction_experiments.classification_completed_at IS 'When classification enrichment was completed';


--
-- Name: COLUMN extraction_experiments.company_name_results_json; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.extraction_experiments.company_name_results_json IS 'JSON object containing company name extraction results for each deck in the experiment';


--
-- Name: COLUMN extraction_experiments.company_name_completed_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.extraction_experiments.company_name_completed_at IS 'When company name extraction was completed';


--
-- Name: COLUMN extraction_experiments.template_processing_results_json; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.extraction_experiments.template_processing_results_json IS 'JSON object containing template processing results for each deck';


--
-- Name: extraction_experiments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.extraction_experiments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: extraction_experiments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.extraction_experiments_id_seq OWNED BY public.extraction_experiments.id;


--
-- Name: gp_template_customizations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gp_template_customizations (
    id integer NOT NULL,
    gp_email character varying(255) NOT NULL,
    base_template_id integer NOT NULL,
    customization_name character varying(255),
    customized_chapters text,
    customized_questions text,
    customized_weights text,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    modified_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: gp_template_customizations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.gp_template_customizations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: gp_template_customizations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.gp_template_customizations_id_seq OWNED BY public.gp_template_customizations.id;


--
-- Name: healthcare_sectors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.healthcare_sectors (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    display_name character varying(255) NOT NULL,
    description text,
    keywords text NOT NULL,
    subcategories text NOT NULL,
    confidence_threshold real DEFAULT 0.75,
    regulatory_requirements text,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    modified_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: healthcare_sectors_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.healthcare_sectors_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: healthcare_sectors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.healthcare_sectors_id_seq OWNED BY public.healthcare_sectors.id;


--
-- Name: healthcare_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.healthcare_templates (
    id integer NOT NULL,
    template_name character varying(255) NOT NULL,
    analysis_prompt text NOT NULL,
    description text,
    healthcare_sector_id integer,
    is_active boolean DEFAULT true,
    is_default boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: healthcare_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.healthcare_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: healthcare_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.healthcare_templates_id_seq OWNED BY public.healthcare_templates.id;


--
-- Name: model_configs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.model_configs (
    id integer NOT NULL,
    model_name character varying,
    model_type character varying,
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


--
-- Name: model_configs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.model_configs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: model_configs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.model_configs_id_seq OWNED BY public.model_configs.id;


--
-- Name: pipeline_prompts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pipeline_prompts (
    id integer NOT NULL,
    stage_name text NOT NULL,
    prompt_text text NOT NULL,
    is_active boolean DEFAULT true,
    created_by text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    prompt_type character varying(50),
    prompt_name character varying(255),
    is_enabled boolean DEFAULT true
);


--
-- Name: pipeline_prompts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pipeline_prompts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pipeline_prompts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pipeline_prompts_id_seq OWNED BY public.pipeline_prompts.id;


--
-- Name: pitch_decks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pitch_decks (
    id integer NOT NULL,
    user_id integer,
    company_id character varying,
    file_name character varying,
    file_path character varying,
    results_file_path character varying,
    s3_url character varying,
    processing_status character varying,
    ai_analysis_results text,
    created_at timestamp without time zone,
    ai_extracted_startup_name character varying(255) DEFAULT NULL::character varying,
    data_source character varying DEFAULT 'startup'::character varying
);


--
-- Name: pitch_decks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pitch_decks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pitch_decks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pitch_decks_id_seq OWNED BY public.pitch_decks.id;


--
-- Name: projects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.projects (
    id integer NOT NULL,
    company_id character varying(255) NOT NULL,
    project_name character varying(255) NOT NULL,
    funding_round character varying(100),
    current_stage_id integer,
    funding_sought text,
    healthcare_sector_id integer,
    company_offering text,
    project_metadata jsonb,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    tags jsonb DEFAULT '[]'::jsonb,
    is_test boolean DEFAULT false
);


--
-- Name: production_projects; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.production_projects AS
 SELECT id,
    company_id,
    project_name,
    funding_round,
    current_stage_id,
    funding_sought,
    healthcare_sector_id,
    company_offering,
    project_metadata,
    is_active,
    created_at,
    updated_at,
    tags,
    is_test
   FROM public.projects
  WHERE ((is_test = false) OR (is_test IS NULL));


--
-- Name: project_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_documents (
    id integer NOT NULL,
    project_id integer NOT NULL,
    document_type character varying(100) NOT NULL,
    file_name character varying(255) NOT NULL,
    file_path text NOT NULL,
    original_filename character varying(255),
    file_size bigint,
    processing_status character varying(50) DEFAULT 'pending'::character varying,
    extracted_data jsonb,
    analysis_results_path text,
    uploaded_by integer NOT NULL,
    upload_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    is_active boolean DEFAULT true
);


--
-- Name: project_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.project_documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: project_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.project_documents_id_seq OWNED BY public.project_documents.id;


--
-- Name: project_interactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_interactions (
    id integer NOT NULL,
    project_id integer NOT NULL,
    interaction_type character varying(100) NOT NULL,
    title character varying(255),
    content text NOT NULL,
    document_id integer,
    created_by integer NOT NULL,
    status character varying(50) DEFAULT 'active'::character varying,
    interaction_metadata jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: project_interactions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.project_interactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: project_interactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.project_interactions_id_seq OWNED BY public.project_interactions.id;


--
-- Name: project_stages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_stages (
    id integer NOT NULL,
    project_id integer NOT NULL,
    stage_name character varying(255) NOT NULL,
    stage_order integer NOT NULL,
    status character varying(50) DEFAULT 'pending'::character varying,
    stage_metadata jsonb,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    stage_template_id integer,
    stage_code character varying(100)
);


--
-- Name: project_progress; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.project_progress AS
 SELECT p.id AS project_id,
    p.company_id,
    p.project_name,
    p.funding_round,
    count(ps.id) AS total_stages,
    count(
        CASE
            WHEN ((ps.status)::text = 'completed'::text) THEN 1
            ELSE NULL::integer
        END) AS completed_stages,
    count(
        CASE
            WHEN ((ps.status)::text = 'active'::text) THEN 1
            ELSE NULL::integer
        END) AS active_stages,
    count(
        CASE
            WHEN ((ps.status)::text = 'pending'::text) THEN 1
            ELSE NULL::integer
        END) AS pending_stages,
    round((((count(
        CASE
            WHEN ((ps.status)::text = 'completed'::text) THEN 1
            ELSE NULL::integer
        END))::numeric / (NULLIF(count(ps.id), 0))::numeric) * (100)::numeric), 2) AS completion_percentage,
    ( SELECT project_stages.stage_name
           FROM public.project_stages
          WHERE ((project_stages.project_id = p.id) AND ((project_stages.status)::text = 'active'::text))
          ORDER BY project_stages.stage_order
         LIMIT 1) AS current_stage_name,
    ( SELECT project_stages.stage_order
           FROM public.project_stages
          WHERE ((project_stages.project_id = p.id) AND ((project_stages.status)::text = 'active'::text))
          ORDER BY project_stages.stage_order
         LIMIT 1) AS current_stage_order
   FROM (public.projects p
     LEFT JOIN public.project_stages ps ON ((p.id = ps.project_id)))
  WHERE (p.is_active = true)
  GROUP BY p.id, p.company_id, p.project_name, p.funding_round;


--
-- Name: project_stages_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.project_stages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: project_stages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.project_stages_id_seq OWNED BY public.project_stages.id;


--
-- Name: projects_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.projects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: projects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.projects_id_seq OWNED BY public.projects.id;


--
-- Name: question_analysis_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.question_analysis_results (
    id integer NOT NULL,
    pitch_deck_id integer NOT NULL,
    question_id integer NOT NULL,
    raw_response text,
    structured_response text,
    score integer,
    confidence_score real,
    processing_time real,
    model_used character varying(100),
    prompt_used text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT question_analysis_results_score_check CHECK (((score >= 0) AND (score <= 7)))
);


--
-- Name: question_analysis_results_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.question_analysis_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: question_analysis_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.question_analysis_results_id_seq OWNED BY public.question_analysis_results.id;


--
-- Name: questions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.questions (
    id integer NOT NULL,
    review_id integer,
    question_text text,
    asked_by integer,
    created_at timestamp without time zone
);


--
-- Name: questions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.questions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.questions_id_seq OWNED BY public.questions.id;


--
-- Name: reviews; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reviews (
    id integer NOT NULL,
    pitch_deck_id integer,
    review_data text,
    s3_review_url character varying,
    status character varying,
    created_at timestamp without time zone
);


--
-- Name: reviews_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.reviews_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: reviews_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.reviews_id_seq OWNED BY public.reviews.id;


--
-- Name: specialized_analysis_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.specialized_analysis_results (
    id integer NOT NULL,
    pitch_deck_id integer NOT NULL,
    analysis_type character varying(100) NOT NULL,
    analysis_result text,
    structured_result text,
    confidence_score real,
    model_used character varying(100),
    processing_time real,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: specialized_analysis_results_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.specialized_analysis_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: specialized_analysis_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.specialized_analysis_results_id_seq OWNED BY public.specialized_analysis_results.id;


--
-- Name: stage_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stage_templates (
    id integer NOT NULL,
    stage_name character varying(255) NOT NULL,
    stage_code character varying(100) NOT NULL,
    description text,
    stage_order integer NOT NULL,
    is_required boolean DEFAULT true,
    estimated_duration_days integer,
    stage_metadata jsonb DEFAULT '{}'::jsonb,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: stage_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.stage_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stage_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.stage_templates_id_seq OWNED BY public.stage_templates.id;


--
-- Name: startup_classifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.startup_classifications (
    id integer NOT NULL,
    pitch_deck_id integer NOT NULL,
    company_offering text NOT NULL,
    primary_sector_id integer,
    subcategory character varying(255),
    confidence_score real,
    classification_reasoning text,
    secondary_sector_id integer,
    keywords_matched text,
    template_used integer,
    manual_override boolean DEFAULT false,
    manual_override_reason text,
    classified_by character varying(255),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: startup_classifications_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.startup_classifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: startup_classifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.startup_classifications_id_seq OWNED BY public.startup_classifications.id;


--
-- Name: template_chapters; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.template_chapters (
    id integer NOT NULL,
    template_id integer NOT NULL,
    chapter_id character varying(100) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    weight real DEFAULT 1.0,
    order_index integer DEFAULT 0,
    is_required boolean DEFAULT true,
    enabled boolean DEFAULT true,
    chapter_prompt_template text,
    scoring_prompt_template text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    modified_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    analysis_template_id integer
);


--
-- Name: template_chapters_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.template_chapters_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: template_chapters_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.template_chapters_id_seq OWNED BY public.template_chapters.id;


--
-- Name: template_performance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.template_performance (
    id integer NOT NULL,
    template_id integer NOT NULL,
    pitch_deck_id integer NOT NULL,
    total_processing_time real,
    successful_questions integer,
    failed_questions integer,
    average_confidence real,
    gp_rating integer,
    gp_feedback text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT template_performance_gp_rating_check CHECK (((gp_rating >= 1) AND (gp_rating <= 5)))
);


--
-- Name: template_performance_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.template_performance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: template_performance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.template_performance_id_seq OWNED BY public.template_performance.id;


--
-- Name: test_projects; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.test_projects AS
 SELECT id,
    company_id,
    project_name,
    funding_round,
    current_stage_id,
    funding_sought,
    healthcare_sector_id,
    company_offering,
    project_metadata,
    is_active,
    created_at,
    updated_at,
    tags,
    is_test
   FROM public.projects
  WHERE (is_test = true);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying,
    password_hash character varying,
    company_name character varying,
    role character varying,
    preferred_language character varying,
    is_verified boolean,
    verification_token character varying,
    verification_token_expires timestamp without time zone,
    created_at timestamp without time zone,
    last_login timestamp without time zone,
    first_name character varying,
    last_name character varying
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: visual_analysis_cache; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.visual_analysis_cache (
    id integer NOT NULL,
    pitch_deck_id integer NOT NULL,
    analysis_result_json text NOT NULL,
    vision_model_used character varying(255) NOT NULL,
    prompt_used text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: TABLE visual_analysis_cache; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.visual_analysis_cache IS 'Caches visual analysis results to avoid re-processing during extraction testing';


--
-- Name: COLUMN visual_analysis_cache.analysis_result_json; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.visual_analysis_cache.analysis_result_json IS 'Full JSON result from visual analysis pipeline';


--
-- Name: COLUMN visual_analysis_cache.vision_model_used; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.visual_analysis_cache.vision_model_used IS 'Name of vision model used for analysis';


--
-- Name: COLUMN visual_analysis_cache.prompt_used; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.visual_analysis_cache.prompt_used IS 'Prompt template used for visual analysis';


--
-- Name: visual_analysis_cache_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.visual_analysis_cache_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: visual_analysis_cache_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.visual_analysis_cache_id_seq OWNED BY public.visual_analysis_cache.id;


--
-- Name: analysis_templates id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_templates ALTER COLUMN id SET DEFAULT nextval('public.analysis_templates_id_seq'::regclass);


--
-- Name: answers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.answers ALTER COLUMN id SET DEFAULT nextval('public.answers_id_seq'::regclass);


--
-- Name: chapter_analysis_results id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chapter_analysis_results ALTER COLUMN id SET DEFAULT nextval('public.chapter_analysis_results_id_seq'::regclass);


--
-- Name: chapter_questions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chapter_questions ALTER COLUMN id SET DEFAULT nextval('public.chapter_questions_id_seq'::regclass);


--
-- Name: classification_performance id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.classification_performance ALTER COLUMN id SET DEFAULT nextval('public.classification_performance_id_seq'::regclass);


--
-- Name: extraction_experiments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_experiments ALTER COLUMN id SET DEFAULT nextval('public.extraction_experiments_id_seq'::regclass);


--
-- Name: gp_template_customizations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gp_template_customizations ALTER COLUMN id SET DEFAULT nextval('public.gp_template_customizations_id_seq'::regclass);


--
-- Name: healthcare_sectors id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.healthcare_sectors ALTER COLUMN id SET DEFAULT nextval('public.healthcare_sectors_id_seq'::regclass);


--
-- Name: healthcare_templates id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.healthcare_templates ALTER COLUMN id SET DEFAULT nextval('public.healthcare_templates_id_seq'::regclass);


--
-- Name: model_configs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_configs ALTER COLUMN id SET DEFAULT nextval('public.model_configs_id_seq'::regclass);


--
-- Name: pipeline_prompts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_prompts ALTER COLUMN id SET DEFAULT nextval('public.pipeline_prompts_id_seq'::regclass);


--
-- Name: pitch_decks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pitch_decks ALTER COLUMN id SET DEFAULT nextval('public.pitch_decks_id_seq'::regclass);


--
-- Name: project_documents id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_documents ALTER COLUMN id SET DEFAULT nextval('public.project_documents_id_seq'::regclass);


--
-- Name: project_interactions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_interactions ALTER COLUMN id SET DEFAULT nextval('public.project_interactions_id_seq'::regclass);


--
-- Name: project_stages id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_stages ALTER COLUMN id SET DEFAULT nextval('public.project_stages_id_seq'::regclass);


--
-- Name: projects id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects ALTER COLUMN id SET DEFAULT nextval('public.projects_id_seq'::regclass);


--
-- Name: question_analysis_results id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question_analysis_results ALTER COLUMN id SET DEFAULT nextval('public.question_analysis_results_id_seq'::regclass);


--
-- Name: questions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.questions ALTER COLUMN id SET DEFAULT nextval('public.questions_id_seq'::regclass);


--
-- Name: reviews id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reviews ALTER COLUMN id SET DEFAULT nextval('public.reviews_id_seq'::regclass);


--
-- Name: specialized_analysis_results id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.specialized_analysis_results ALTER COLUMN id SET DEFAULT nextval('public.specialized_analysis_results_id_seq'::regclass);


--
-- Name: stage_templates id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stage_templates ALTER COLUMN id SET DEFAULT nextval('public.stage_templates_id_seq'::regclass);


--
-- Name: startup_classifications id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.startup_classifications ALTER COLUMN id SET DEFAULT nextval('public.startup_classifications_id_seq'::regclass);


--
-- Name: template_chapters id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.template_chapters ALTER COLUMN id SET DEFAULT nextval('public.template_chapters_id_seq'::regclass);


--
-- Name: template_performance id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.template_performance ALTER COLUMN id SET DEFAULT nextval('public.template_performance_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: visual_analysis_cache id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.visual_analysis_cache ALTER COLUMN id SET DEFAULT nextval('public.visual_analysis_cache_id_seq'::regclass);


--
-- Name: analysis_templates analysis_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_templates
    ADD CONSTRAINT analysis_templates_pkey PRIMARY KEY (id);


--
-- Name: answers answers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.answers
    ADD CONSTRAINT answers_pkey PRIMARY KEY (id);


--
-- Name: chapter_analysis_results chapter_analysis_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chapter_analysis_results
    ADD CONSTRAINT chapter_analysis_results_pkey PRIMARY KEY (id);


--
-- Name: chapter_questions chapter_questions_chapter_id_question_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chapter_questions
    ADD CONSTRAINT chapter_questions_chapter_id_question_id_key UNIQUE (chapter_id, question_id);


--
-- Name: chapter_questions chapter_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chapter_questions
    ADD CONSTRAINT chapter_questions_pkey PRIMARY KEY (id);


--
-- Name: classification_performance classification_performance_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.classification_performance
    ADD CONSTRAINT classification_performance_pkey PRIMARY KEY (id);


--
-- Name: extraction_experiments extraction_experiments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_experiments
    ADD CONSTRAINT extraction_experiments_pkey PRIMARY KEY (id);


--
-- Name: gp_template_customizations gp_template_customizations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gp_template_customizations
    ADD CONSTRAINT gp_template_customizations_pkey PRIMARY KEY (id);


--
-- Name: healthcare_sectors healthcare_sectors_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.healthcare_sectors
    ADD CONSTRAINT healthcare_sectors_name_key UNIQUE (name);


--
-- Name: healthcare_sectors healthcare_sectors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.healthcare_sectors
    ADD CONSTRAINT healthcare_sectors_pkey PRIMARY KEY (id);


--
-- Name: healthcare_templates healthcare_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.healthcare_templates
    ADD CONSTRAINT healthcare_templates_pkey PRIMARY KEY (id);


--
-- Name: model_configs model_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_configs
    ADD CONSTRAINT model_configs_pkey PRIMARY KEY (id);


--
-- Name: pipeline_prompts pipeline_prompts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_prompts
    ADD CONSTRAINT pipeline_prompts_pkey PRIMARY KEY (id);


--
-- Name: pitch_decks pitch_decks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pitch_decks
    ADD CONSTRAINT pitch_decks_pkey PRIMARY KEY (id);


--
-- Name: project_documents project_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_documents
    ADD CONSTRAINT project_documents_pkey PRIMARY KEY (id);


--
-- Name: project_interactions project_interactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_interactions
    ADD CONSTRAINT project_interactions_pkey PRIMARY KEY (id);


--
-- Name: project_stages project_stages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_stages
    ADD CONSTRAINT project_stages_pkey PRIMARY KEY (id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: question_analysis_results question_analysis_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question_analysis_results
    ADD CONSTRAINT question_analysis_results_pkey PRIMARY KEY (id);


--
-- Name: questions questions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT questions_pkey PRIMARY KEY (id);


--
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);


--
-- Name: specialized_analysis_results specialized_analysis_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.specialized_analysis_results
    ADD CONSTRAINT specialized_analysis_results_pkey PRIMARY KEY (id);


--
-- Name: stage_templates stage_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stage_templates
    ADD CONSTRAINT stage_templates_pkey PRIMARY KEY (id);


--
-- Name: stage_templates stage_templates_stage_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stage_templates
    ADD CONSTRAINT stage_templates_stage_code_key UNIQUE (stage_code);


--
-- Name: startup_classifications startup_classifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.startup_classifications
    ADD CONSTRAINT startup_classifications_pkey PRIMARY KEY (id);


--
-- Name: template_chapters template_chapters_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.template_chapters
    ADD CONSTRAINT template_chapters_pkey PRIMARY KEY (id);


--
-- Name: template_chapters template_chapters_template_id_chapter_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.template_chapters
    ADD CONSTRAINT template_chapters_template_id_chapter_id_key UNIQUE (template_id, chapter_id);


--
-- Name: template_performance template_performance_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.template_performance
    ADD CONSTRAINT template_performance_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: visual_analysis_cache visual_analysis_cache_pitch_deck_id_vision_model_used_promp_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.visual_analysis_cache
    ADD CONSTRAINT visual_analysis_cache_pitch_deck_id_vision_model_used_promp_key UNIQUE (pitch_deck_id, vision_model_used, prompt_used);


--
-- Name: visual_analysis_cache visual_analysis_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.visual_analysis_cache
    ADD CONSTRAINT visual_analysis_cache_pkey PRIMARY KEY (id);


--
-- Name: idx_extraction_experiments_classification_completed_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_extraction_experiments_classification_completed_at ON public.extraction_experiments USING btree (classification_completed_at DESC);


--
-- Name: idx_extraction_experiments_classification_enabled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_extraction_experiments_classification_enabled ON public.extraction_experiments USING btree (classification_enabled);


--
-- Name: idx_extraction_experiments_company_name_completed_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_extraction_experiments_company_name_completed_at ON public.extraction_experiments USING btree (company_name_completed_at DESC);


--
-- Name: idx_extraction_experiments_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_extraction_experiments_created_at ON public.extraction_experiments USING btree (created_at DESC);


--
-- Name: idx_extraction_experiments_deck_date_completed_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_extraction_experiments_deck_date_completed_at ON public.extraction_experiments USING btree (deck_date_completed_at DESC);


--
-- Name: idx_extraction_experiments_funding_amount_completed_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_extraction_experiments_funding_amount_completed_at ON public.extraction_experiments USING btree (funding_amount_completed_at DESC);


--
-- Name: idx_extraction_experiments_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_extraction_experiments_name ON public.extraction_experiments USING btree (experiment_name);


--
-- Name: idx_extraction_experiments_template_completed; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_extraction_experiments_template_completed ON public.extraction_experiments USING btree (template_processing_completed_at);


--
-- Name: idx_healthcare_templates_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_healthcare_templates_active ON public.healthcare_templates USING btree (is_active);


--
-- Name: idx_healthcare_templates_default; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_healthcare_templates_default ON public.healthcare_templates USING btree (is_default);


--
-- Name: idx_pitch_decks_ai_extracted_startup_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pitch_decks_ai_extracted_startup_name ON public.pitch_decks USING btree (ai_extracted_startup_name);


--
-- Name: idx_project_documents_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_documents_project_id ON public.project_documents USING btree (project_id);


--
-- Name: idx_project_documents_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_documents_type ON public.project_documents USING btree (document_type);


--
-- Name: idx_project_documents_uploaded_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_documents_uploaded_by ON public.project_documents USING btree (uploaded_by);


--
-- Name: idx_project_interactions_created_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_interactions_created_by ON public.project_interactions USING btree (created_by);


--
-- Name: idx_project_interactions_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_interactions_project_id ON public.project_interactions USING btree (project_id);


--
-- Name: idx_project_interactions_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_interactions_type ON public.project_interactions USING btree (interaction_type);


--
-- Name: idx_project_stages_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_stages_order ON public.project_stages USING btree (project_id, stage_order);


--
-- Name: idx_project_stages_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_stages_project_id ON public.project_stages USING btree (project_id);


--
-- Name: idx_projects_company_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_company_id ON public.projects USING btree (company_id);


--
-- Name: idx_projects_funding_round; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_funding_round ON public.projects USING btree (funding_round);


--
-- Name: idx_projects_is_test; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_is_test ON public.projects USING btree (is_test);


--
-- Name: idx_projects_tags_gin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_tags_gin ON public.projects USING gin (tags);


--
-- Name: idx_stage_templates_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stage_templates_active ON public.stage_templates USING btree (is_active);


--
-- Name: idx_stage_templates_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stage_templates_code ON public.stage_templates USING btree (stage_code);


--
-- Name: idx_stage_templates_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stage_templates_order ON public.stage_templates USING btree (stage_order);


--
-- Name: idx_visual_analysis_cache_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_visual_analysis_cache_created_at ON public.visual_analysis_cache USING btree (created_at DESC);


--
-- Name: idx_visual_analysis_cache_pitch_deck_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_visual_analysis_cache_pitch_deck_id ON public.visual_analysis_cache USING btree (pitch_deck_id);


--
-- Name: ix_answers_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_answers_id ON public.answers USING btree (id);


--
-- Name: ix_model_configs_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_model_configs_id ON public.model_configs USING btree (id);


--
-- Name: ix_model_configs_model_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_model_configs_model_name ON public.model_configs USING btree (model_name);


--
-- Name: ix_model_configs_model_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_model_configs_model_type ON public.model_configs USING btree (model_type);


--
-- Name: ix_pitch_decks_company_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pitch_decks_company_id ON public.pitch_decks USING btree (company_id);


--
-- Name: ix_pitch_decks_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pitch_decks_id ON public.pitch_decks USING btree (id);


--
-- Name: ix_questions_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_questions_id ON public.questions USING btree (id);


--
-- Name: ix_reviews_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_reviews_id ON public.reviews USING btree (id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_users_verification_token; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_verification_token ON public.users USING btree (verification_token);


--
-- Name: projects trigger_auto_initialize_stages; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_auto_initialize_stages AFTER INSERT ON public.projects FOR EACH ROW EXECUTE FUNCTION public.auto_initialize_project_stages();


--
-- Name: analysis_templates analysis_templates_healthcare_sector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_templates
    ADD CONSTRAINT analysis_templates_healthcare_sector_id_fkey FOREIGN KEY (healthcare_sector_id) REFERENCES public.healthcare_sectors(id);


--
-- Name: answers answers_answered_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.answers
    ADD CONSTRAINT answers_answered_by_fkey FOREIGN KEY (answered_by) REFERENCES public.users(id);


--
-- Name: answers answers_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.answers
    ADD CONSTRAINT answers_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.questions(id);


--
-- Name: chapter_analysis_results chapter_analysis_results_chapter_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chapter_analysis_results
    ADD CONSTRAINT chapter_analysis_results_chapter_id_fkey FOREIGN KEY (chapter_id) REFERENCES public.template_chapters(id);


--
-- Name: chapter_analysis_results chapter_analysis_results_pitch_deck_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chapter_analysis_results
    ADD CONSTRAINT chapter_analysis_results_pitch_deck_id_fkey FOREIGN KEY (pitch_deck_id) REFERENCES public.pitch_decks(id);


--
-- Name: chapter_questions chapter_questions_chapter_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chapter_questions
    ADD CONSTRAINT chapter_questions_chapter_id_fkey FOREIGN KEY (chapter_id) REFERENCES public.template_chapters(id);


--
-- Name: classification_performance classification_performance_classification_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.classification_performance
    ADD CONSTRAINT classification_performance_classification_id_fkey FOREIGN KEY (classification_id) REFERENCES public.startup_classifications(id);


--
-- Name: gp_template_customizations gp_template_customizations_base_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gp_template_customizations
    ADD CONSTRAINT gp_template_customizations_base_template_id_fkey FOREIGN KEY (base_template_id) REFERENCES public.analysis_templates(id);


--
-- Name: pitch_decks pitch_decks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pitch_decks
    ADD CONSTRAINT pitch_decks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: project_documents project_documents_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_documents
    ADD CONSTRAINT project_documents_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: project_documents project_documents_uploaded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_documents
    ADD CONSTRAINT project_documents_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.users(id);


--
-- Name: project_interactions project_interactions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_interactions
    ADD CONSTRAINT project_interactions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: project_interactions project_interactions_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_interactions
    ADD CONSTRAINT project_interactions_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.project_documents(id);


--
-- Name: project_interactions project_interactions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_interactions
    ADD CONSTRAINT project_interactions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: project_stages project_stages_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_stages
    ADD CONSTRAINT project_stages_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: project_stages project_stages_stage_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_stages
    ADD CONSTRAINT project_stages_stage_template_id_fkey FOREIGN KEY (stage_template_id) REFERENCES public.stage_templates(id);


--
-- Name: question_analysis_results question_analysis_results_pitch_deck_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question_analysis_results
    ADD CONSTRAINT question_analysis_results_pitch_deck_id_fkey FOREIGN KEY (pitch_deck_id) REFERENCES public.pitch_decks(id);


--
-- Name: question_analysis_results question_analysis_results_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question_analysis_results
    ADD CONSTRAINT question_analysis_results_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.chapter_questions(id);


--
-- Name: questions questions_asked_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT questions_asked_by_fkey FOREIGN KEY (asked_by) REFERENCES public.users(id);


--
-- Name: questions questions_review_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT questions_review_id_fkey FOREIGN KEY (review_id) REFERENCES public.reviews(id);


--
-- Name: reviews reviews_pitch_deck_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pitch_deck_id_fkey FOREIGN KEY (pitch_deck_id) REFERENCES public.pitch_decks(id);


--
-- Name: specialized_analysis_results specialized_analysis_results_pitch_deck_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.specialized_analysis_results
    ADD CONSTRAINT specialized_analysis_results_pitch_deck_id_fkey FOREIGN KEY (pitch_deck_id) REFERENCES public.pitch_decks(id);


--
-- Name: startup_classifications startup_classifications_pitch_deck_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.startup_classifications
    ADD CONSTRAINT startup_classifications_pitch_deck_id_fkey FOREIGN KEY (pitch_deck_id) REFERENCES public.pitch_decks(id);


--
-- Name: startup_classifications startup_classifications_primary_sector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.startup_classifications
    ADD CONSTRAINT startup_classifications_primary_sector_id_fkey FOREIGN KEY (primary_sector_id) REFERENCES public.healthcare_sectors(id);


--
-- Name: startup_classifications startup_classifications_secondary_sector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.startup_classifications
    ADD CONSTRAINT startup_classifications_secondary_sector_id_fkey FOREIGN KEY (secondary_sector_id) REFERENCES public.healthcare_sectors(id);


--
-- Name: startup_classifications startup_classifications_template_used_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.startup_classifications
    ADD CONSTRAINT startup_classifications_template_used_fkey FOREIGN KEY (template_used) REFERENCES public.analysis_templates(id);


--
-- Name: template_chapters template_chapters_analysis_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.template_chapters
    ADD CONSTRAINT template_chapters_analysis_template_id_fkey FOREIGN KEY (analysis_template_id) REFERENCES public.analysis_templates(id);


--
-- Name: template_chapters template_chapters_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.template_chapters
    ADD CONSTRAINT template_chapters_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.analysis_templates(id);


--
-- Name: template_performance template_performance_pitch_deck_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.template_performance
    ADD CONSTRAINT template_performance_pitch_deck_id_fkey FOREIGN KEY (pitch_deck_id) REFERENCES public.pitch_decks(id);


--
-- Name: template_performance template_performance_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.template_performance
    ADD CONSTRAINT template_performance_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.analysis_templates(id);


--
-- Name: visual_analysis_cache visual_analysis_cache_pitch_deck_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.visual_analysis_cache
    ADD CONSTRAINT visual_analysis_cache_pitch_deck_id_fkey FOREIGN KEY (pitch_deck_id) REFERENCES public.pitch_decks(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

