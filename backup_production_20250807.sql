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
-- Name: auto_initialize_project_stages(); Type: FUNCTION; Schema: public; Owner: review_user
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


ALTER FUNCTION public.auto_initialize_project_stages() OWNER TO review_user;

--
-- Name: cleanup_expired_locks(); Type: FUNCTION; Schema: public; Owner: review_user
--

CREATE FUNCTION public.cleanup_expired_locks() RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
cleaned_count INTEGER;
BEGIN
UPDATE processing_queue
SET
locked_by = NULL,
locked_at = NULL,
lock_expires_at = NULL,
status = CASE
WHEN status = 'processing' THEN 'queued'  -- Reset to queued for retry
ELSE status
END
WHERE
locked_by IS NOT NULL
AND lock_expires_at < CURRENT_TIMESTAMP;
GET DIAGNOSTICS cleaned_count = ROW_COUNT;
RETURN cleaned_count;
END;
$$;


ALTER FUNCTION public.cleanup_expired_locks() OWNER TO review_user;

--
-- Name: complete_task(integer, boolean, text, text, jsonb); Type: FUNCTION; Schema: public; Owner: review_user
--

CREATE FUNCTION public.complete_task(task_id integer, success boolean, results_path text DEFAULT NULL::text, error_message text DEFAULT NULL::text, metadata jsonb DEFAULT '{}'::jsonb) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE
deck_id INTEGER;
BEGIN
UPDATE processing_queue
SET
status = CASE WHEN success THEN 'completed' ELSE 'failed' END,
completed_at = CURRENT_TIMESTAMP,
progress_percentage = CASE WHEN success THEN 100 ELSE progress_percentage END,
results_file_path = results_path,
last_error = error_message,
error_count = CASE WHEN success THEN error_count ELSE error_count + 1 END,
processing_metadata = metadata,
locked_by = NULL,
locked_at = NULL,
lock_expires_at = NULL
WHERE id = task_id
RETURNING pitch_deck_id INTO deck_id;
IF FOUND AND success THEN
UPDATE pitch_decks
SET
processing_status = 'completed',
results_file_path = results_path,
current_processing_task_id = NULL
WHERE id = deck_id;
ELSIF FOUND AND NOT success THEN
UPDATE pitch_decks
SET processing_status = 'failed'
WHERE id = deck_id;
END IF;
RETURN FOUND;
END;
$$;


ALTER FUNCTION public.complete_task(task_id integer, success boolean, results_path text, error_message text, metadata jsonb) OWNER TO review_user;

--
-- Name: get_next_processing_task(character varying, jsonb); Type: FUNCTION; Schema: public; Owner: review_user
--

CREATE FUNCTION public.get_next_processing_task(server_id character varying, server_capabilities jsonb DEFAULT '{}'::jsonb) RETURNS TABLE(task_id integer, pitch_deck_id integer, task_type character varying, file_path text, company_id character varying, processing_options jsonb)
    LANGUAGE plpgsql
    AS $$
DECLARE
    lock_duration INTERVAL := '30 minutes';
    selected_task_id INTEGER;
BEGIN
    -- Clean up any expired locks first
    PERFORM cleanup_expired_locks();
    
    -- Find the next available task (without locking yet)
    SELECT pq.id INTO selected_task_id
    FROM processing_queue pq
    WHERE 
        pq.status IN ('queued', 'retry') 
        AND (pq.next_retry_at IS NULL OR pq.next_retry_at <= CURRENT_TIMESTAMP)
        AND pq.locked_by IS NULL
        -- Check dependencies separately to avoid LEFT JOIN issues
        AND NOT EXISTS (
            SELECT 1 FROM task_dependencies td
            WHERE td.dependent_task_id = pq.id
            AND EXISTS (
                SELECT 1 FROM processing_queue dep 
                WHERE dep.id = td.depends_on_task_id 
                AND dep.status != 'completed'
            )
        )
    ORDER BY pq.priority DESC, pq.created_at ASC
    LIMIT 1;
    
    -- If no task found, return empty
    IF selected_task_id IS NULL THEN
        RETURN;
    END IF;
    
    -- Lock and update the selected task
    UPDATE processing_queue 
    SET 
        locked_by = server_id,
        locked_at = CURRENT_TIMESTAMP,
        lock_expires_at = CURRENT_TIMESTAMP + lock_duration,
        status = 'processing',
        started_at = CASE WHEN started_at IS NULL THEN CURRENT_TIMESTAMP ELSE started_at END
    WHERE id = selected_task_id
    AND locked_by IS NULL  -- Double-check it's still unlocked
    RETURNING 
        processing_queue.id,
        processing_queue.pitch_deck_id,
        processing_queue.task_type,
        processing_queue.file_path,
        processing_queue.company_id,
        processing_queue.processing_options
    INTO task_id, pitch_deck_id, task_type, file_path, company_id, processing_options;
    
    -- Return the task if we successfully locked it
    IF task_id IS NOT NULL THEN
        RETURN NEXT;
    END IF;
END;
$$;


ALTER FUNCTION public.get_next_processing_task(server_id character varying, server_capabilities jsonb) OWNER TO review_user;

--
-- Name: initialize_project_stages(integer); Type: FUNCTION; Schema: public; Owner: review_user
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


ALTER FUNCTION public.initialize_project_stages(project_id_param integer) OWNER TO review_user;

--
-- Name: retry_failed_task(integer); Type: FUNCTION; Schema: public; Owner: review_user
--

CREATE FUNCTION public.retry_failed_task(task_id integer) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
UPDATE processing_queue
SET
status = 'retry',
retry_count = retry_count + 1,
next_retry_at = CURRENT_TIMESTAMP + (INTERVAL '5 minutes' * POWER(2, retry_count)), -- Exponential backoff
locked_by = NULL,
locked_at = NULL,
lock_expires_at = NULL
WHERE
id = task_id
AND status = 'failed'
AND retry_count < max_retries;
RETURN FOUND;
END;
$$;


ALTER FUNCTION public.retry_failed_task(task_id integer) OWNER TO review_user;

--
-- Name: update_task_progress(integer, integer, character varying, text, jsonb); Type: FUNCTION; Schema: public; Owner: review_user
--

CREATE FUNCTION public.update_task_progress(task_id integer, new_progress integer, step_name character varying DEFAULT NULL::character varying, message text DEFAULT NULL::text, step_data jsonb DEFAULT '{}'::jsonb) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
UPDATE processing_queue
SET
progress_percentage = new_progress,
current_step = COALESCE(step_name, current_step),
progress_message = COALESCE(message, progress_message),
lock_expires_at = CURRENT_TIMESTAMP + INTERVAL '30 minutes' -- Extend lock
WHERE id = task_id;
IF step_name IS NOT NULL THEN
INSERT INTO processing_progress (
processing_queue_id, step_name, step_status,
progress_percentage, message, step_data
) VALUES (
task_id, step_name, 'started',
new_progress, message, step_data
);
END IF;
RETURN FOUND;
END;
$$;


ALTER FUNCTION public.update_task_progress(task_id integer, new_progress integer, step_name character varying, message text, step_data jsonb) OWNER TO review_user;

--
-- Name: update_template_configurations_updated_at(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_template_configurations_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_template_configurations_updated_at() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: analysis_templates; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.analysis_templates (
    id integer NOT NULL,
    healthcare_sector_id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    template_version character varying(50),
    specialized_analysis text,
    is_active boolean,
    is_default boolean,
    usage_count integer,
    created_by character varying(255),
    created_at timestamp without time zone,
    modified_at timestamp without time zone,
    analysis_prompt text
);


ALTER TABLE public.analysis_templates OWNER TO review_user;

--
-- Name: analysis_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.analysis_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.analysis_templates_id_seq OWNER TO review_user;

--
-- Name: analysis_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.analysis_templates_id_seq OWNED BY public.analysis_templates.id;


--
-- Name: answers; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.answers (
    id integer NOT NULL,
    question_id integer,
    answer_text text,
    answered_by integer,
    created_at timestamp without time zone
);


ALTER TABLE public.answers OWNER TO review_user;

--
-- Name: answers_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.answers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.answers_id_seq OWNER TO review_user;

--
-- Name: answers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.answers_id_seq OWNED BY public.answers.id;


--
-- Name: chapter_analysis_results; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.chapter_analysis_results (
    id integer NOT NULL,
    pitch_deck_id integer NOT NULL,
    chapter_id integer NOT NULL,
    chapter_response text,
    average_score numeric,
    weighted_score numeric,
    total_questions integer,
    answered_questions integer,
    processing_time numeric,
    created_at timestamp without time zone
);


ALTER TABLE public.chapter_analysis_results OWNER TO review_user;

--
-- Name: chapter_analysis_results_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.chapter_analysis_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chapter_analysis_results_id_seq OWNER TO review_user;

--
-- Name: chapter_analysis_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.chapter_analysis_results_id_seq OWNED BY public.chapter_analysis_results.id;


--
-- Name: chapter_questions; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.chapter_questions (
    id integer NOT NULL,
    chapter_id integer NOT NULL,
    question_id character varying(100) NOT NULL,
    question_text text NOT NULL,
    weight numeric,
    order_index integer,
    enabled boolean,
    scoring_criteria text,
    healthcare_focus text,
    question_prompt_template text,
    created_at timestamp without time zone,
    modified_at timestamp without time zone
);


ALTER TABLE public.chapter_questions OWNER TO review_user;

--
-- Name: chapter_questions_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.chapter_questions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chapter_questions_id_seq OWNER TO review_user;

--
-- Name: chapter_questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.chapter_questions_id_seq OWNED BY public.chapter_questions.id;


--
-- Name: classification_performance; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.classification_performance (
    id integer NOT NULL,
    classification_id integer NOT NULL,
    was_accurate boolean,
    manual_correction_from character varying(255),
    manual_correction_to character varying(255),
    correction_reason text,
    corrected_by character varying(255),
    created_at timestamp without time zone
);


ALTER TABLE public.classification_performance OWNER TO review_user;

--
-- Name: classification_performance_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.classification_performance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.classification_performance_id_seq OWNER TO review_user;

--
-- Name: classification_performance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.classification_performance_id_seq OWNED BY public.classification_performance.id;


--
-- Name: extraction_experiments; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.extraction_experiments (
    id integer NOT NULL,
    experiment_name character varying(255) NOT NULL,
    pitch_deck_ids text NOT NULL,
    extraction_type character varying(50) NOT NULL,
    text_model_used character varying(255) NOT NULL,
    extraction_prompt text NOT NULL,
    results_json text NOT NULL,
    created_at timestamp without time zone,
    classification_enabled boolean DEFAULT false,
    classification_results_json text,
    classification_completed_at timestamp without time zone,
    company_name_results_json text,
    company_name_completed_at timestamp without time zone,
    funding_amount_results_json text,
    funding_amount_completed_at timestamp without time zone,
    deck_date_results_json text,
    deck_date_completed_at timestamp without time zone,
    template_processing_results_json text,
    classification_model_used character varying(255),
    template_processing_completed_at timestamp without time zone
);


ALTER TABLE public.extraction_experiments OWNER TO review_user;

--
-- Name: extraction_experiments_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.extraction_experiments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.extraction_experiments_id_seq OWNER TO review_user;

--
-- Name: extraction_experiments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.extraction_experiments_id_seq OWNED BY public.extraction_experiments.id;


--
-- Name: gp_template_customizations; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.gp_template_customizations (
    id integer NOT NULL,
    gp_email character varying(255) NOT NULL,
    base_template_id integer NOT NULL,
    customization_name character varying(255),
    customized_chapters text,
    customized_questions text,
    customized_weights text,
    is_active boolean,
    created_at timestamp without time zone,
    modified_at timestamp without time zone
);


ALTER TABLE public.gp_template_customizations OWNER TO review_user;

--
-- Name: gp_template_customizations_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.gp_template_customizations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.gp_template_customizations_id_seq OWNER TO review_user;

--
-- Name: gp_template_customizations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.gp_template_customizations_id_seq OWNED BY public.gp_template_customizations.id;


--
-- Name: healthcare_sectors; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.healthcare_sectors (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    display_name character varying(255) NOT NULL,
    description text,
    keywords text NOT NULL,
    subcategories text NOT NULL,
    confidence_threshold numeric,
    regulatory_requirements text,
    is_active boolean,
    created_at timestamp without time zone,
    modified_at timestamp without time zone
);


ALTER TABLE public.healthcare_sectors OWNER TO review_user;

--
-- Name: healthcare_sectors_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.healthcare_sectors_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.healthcare_sectors_id_seq OWNER TO review_user;

--
-- Name: healthcare_sectors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.healthcare_sectors_id_seq OWNED BY public.healthcare_sectors.id;


--
-- Name: healthcare_templates_deprecated; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.healthcare_templates_deprecated (
    id integer NOT NULL,
    template_name character varying(255) NOT NULL,
    analysis_prompt text NOT NULL,
    description text,
    healthcare_sector_id integer,
    is_active boolean,
    is_default boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.healthcare_templates_deprecated OWNER TO review_user;

--
-- Name: healthcare_templates_deprecated_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.healthcare_templates_deprecated_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.healthcare_templates_deprecated_id_seq OWNER TO review_user;

--
-- Name: healthcare_templates_deprecated_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.healthcare_templates_deprecated_id_seq OWNED BY public.healthcare_templates_deprecated.id;


--
-- Name: model_configs; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.model_configs (
    id integer NOT NULL,
    model_name character varying,
    model_type character varying,
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.model_configs OWNER TO review_user;

--
-- Name: model_configs_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.model_configs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.model_configs_id_seq OWNER TO review_user;

--
-- Name: model_configs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.model_configs_id_seq OWNED BY public.model_configs.id;


--
-- Name: pipeline_prompts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pipeline_prompts (
    id integer NOT NULL,
    stage_name text NOT NULL,
    prompt_text text NOT NULL,
    is_active boolean DEFAULT true,
    created_by text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    prompt_type character varying(255),
    prompt_name character varying(255),
    is_enabled boolean DEFAULT true
);


ALTER TABLE public.pipeline_prompts OWNER TO postgres;

--
-- Name: pipeline_prompts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.pipeline_prompts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pipeline_prompts_id_seq OWNER TO postgres;

--
-- Name: pipeline_prompts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.pipeline_prompts_id_seq OWNED BY public.pipeline_prompts.id;


--
-- Name: pitch_decks; Type: TABLE; Schema: public; Owner: review_user
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
    ai_extracted_startup_name character varying,
    data_source character varying,
    zip_filename character varying,
    created_at timestamp without time zone,
    template_processing_results_json text,
    current_processing_task_id integer
);


ALTER TABLE public.pitch_decks OWNER TO review_user;

--
-- Name: pitch_decks_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.pitch_decks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pitch_decks_id_seq OWNER TO review_user;

--
-- Name: pitch_decks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.pitch_decks_id_seq OWNED BY public.pitch_decks.id;


--
-- Name: processing_progress; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.processing_progress (
    id integer NOT NULL,
    processing_queue_id integer NOT NULL,
    step_name character varying(255) NOT NULL,
    step_status character varying(20) NOT NULL,
    progress_percentage integer DEFAULT 0,
    message text,
    step_data jsonb DEFAULT '{}'::jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.processing_progress OWNER TO review_user;

--
-- Name: TABLE processing_progress; Type: COMMENT; Schema: public; Owner: review_user
--

COMMENT ON TABLE public.processing_progress IS 'Detailed progress tracking for each processing step';


--
-- Name: processing_progress_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.processing_progress_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.processing_progress_id_seq OWNER TO review_user;

--
-- Name: processing_progress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.processing_progress_id_seq OWNED BY public.processing_progress.id;


--
-- Name: processing_queue; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.processing_queue (
    id integer NOT NULL,
    pitch_deck_id integer NOT NULL,
    task_type character varying(50) DEFAULT 'pdf_analysis'::character varying NOT NULL,
    status character varying(20) DEFAULT 'queued'::character varying NOT NULL,
    priority integer DEFAULT 1 NOT NULL,
    file_path text NOT NULL,
    company_id character varying(255) NOT NULL,
    processing_options jsonb DEFAULT '{}'::jsonb,
    progress_percentage integer DEFAULT 0,
    current_step character varying(255),
    progress_message text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    retry_count integer DEFAULT 0,
    max_retries integer DEFAULT 3,
    next_retry_at timestamp without time zone,
    last_error text,
    error_count integer DEFAULT 0,
    locked_by character varying(255),
    locked_at timestamp without time zone,
    lock_expires_at timestamp without time zone,
    results_file_path text,
    processing_metadata jsonb DEFAULT '{}'::jsonb,
    template_id_used integer,
    template_source character varying(50)
);


ALTER TABLE public.processing_queue OWNER TO review_user;

--
-- Name: TABLE processing_queue; Type: COMMENT; Schema: public; Owner: review_user
--

COMMENT ON TABLE public.processing_queue IS 'Persistent task queue for PDF processing that survives server restarts';


--
-- Name: COLUMN processing_queue.template_id_used; Type: COMMENT; Schema: public; Owner: review_user
--

COMMENT ON COLUMN public.processing_queue.template_id_used IS 'Actual template ID used for processing (for analytics)';


--
-- Name: COLUMN processing_queue.template_source; Type: COMMENT; Schema: public; Owner: review_user
--

COMMENT ON COLUMN public.processing_queue.template_source IS 'How template was selected: user_override, classification, or fallback';


--
-- Name: processing_queue_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.processing_queue_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.processing_queue_id_seq OWNER TO review_user;

--
-- Name: processing_queue_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.processing_queue_id_seq OWNED BY public.processing_queue.id;


--
-- Name: processing_servers; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.processing_servers (
    id character varying(255) NOT NULL,
    server_type character varying(50) NOT NULL,
    status character varying(20) DEFAULT 'active'::character varying NOT NULL,
    last_heartbeat timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    capabilities jsonb DEFAULT '{}'::jsonb,
    current_load integer DEFAULT 0,
    max_concurrent_tasks integer DEFAULT 5,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.processing_servers OWNER TO review_user;

--
-- Name: TABLE processing_servers; Type: COMMENT; Schema: public; Owner: review_user
--

COMMENT ON TABLE public.processing_servers IS 'Active server instances for distributed processing';


--
-- Name: production_projects; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.production_projects (
    id integer NOT NULL,
    company_id character varying(255),
    project_name character varying(255),
    funding_round character varying(100),
    current_stage_id integer,
    funding_sought text,
    healthcare_sector_id integer,
    company_offering text,
    project_metadata jsonb,
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    tags jsonb,
    is_test boolean
);


ALTER TABLE public.production_projects OWNER TO review_user;

--
-- Name: production_projects_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.production_projects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.production_projects_id_seq OWNER TO review_user;

--
-- Name: production_projects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.production_projects_id_seq OWNED BY public.production_projects.id;


--
-- Name: project_documents; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.project_documents (
    id integer NOT NULL,
    project_id integer,
    document_type character varying,
    file_name character varying,
    file_path character varying,
    original_filename character varying,
    file_size integer,
    processing_status character varying,
    extracted_data text,
    analysis_results_path character varying,
    uploaded_by integer,
    upload_date timestamp without time zone,
    is_active boolean
);


ALTER TABLE public.project_documents OWNER TO review_user;

--
-- Name: project_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.project_documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.project_documents_id_seq OWNER TO review_user;

--
-- Name: project_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.project_documents_id_seq OWNED BY public.project_documents.id;


--
-- Name: project_interactions; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.project_interactions (
    id integer NOT NULL,
    project_id integer,
    interaction_type character varying,
    title character varying,
    content text,
    document_id integer,
    created_by integer,
    status character varying,
    interaction_metadata text,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.project_interactions OWNER TO review_user;

--
-- Name: project_interactions_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.project_interactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.project_interactions_id_seq OWNER TO review_user;

--
-- Name: project_interactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.project_interactions_id_seq OWNED BY public.project_interactions.id;


--
-- Name: project_invitations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.project_invitations (
    id integer NOT NULL,
    invitation_token character varying(255) NOT NULL,
    project_id integer NOT NULL,
    email character varying(255) NOT NULL,
    invited_by_id integer NOT NULL,
    status character varying(50) DEFAULT 'pending'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    accepted_at timestamp without time zone,
    expires_at timestamp without time zone NOT NULL,
    accepted_by_id integer,
    CONSTRAINT project_invitations_status_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'accepted'::character varying, 'expired'::character varying, 'cancelled'::character varying])::text[])))
);


ALTER TABLE public.project_invitations OWNER TO postgres;

--
-- Name: project_invitations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.project_invitations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.project_invitations_id_seq OWNER TO postgres;

--
-- Name: project_invitations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.project_invitations_id_seq OWNED BY public.project_invitations.id;


--
-- Name: project_members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.project_members (
    id integer NOT NULL,
    project_id integer NOT NULL,
    user_id integer NOT NULL,
    role character varying(50) DEFAULT 'member'::character varying,
    added_by_id integer,
    added_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT project_members_role_check CHECK (((role)::text = ANY ((ARRAY['owner'::character varying, 'member'::character varying, 'viewer'::character varying])::text[])))
);


ALTER TABLE public.project_members OWNER TO postgres;

--
-- Name: project_members_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.project_members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.project_members_id_seq OWNER TO postgres;

--
-- Name: project_members_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.project_members_id_seq OWNED BY public.project_members.id;


--
-- Name: project_stages; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.project_stages (
    id integer NOT NULL,
    project_id integer,
    stage_name character varying,
    stage_order integer,
    status character varying,
    stage_metadata text,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    created_at timestamp without time zone,
    stage_template_id integer,
    stage_code character varying(50)
);


ALTER TABLE public.project_stages OWNER TO review_user;

--
-- Name: projects; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.projects (
    id integer NOT NULL,
    company_id character varying,
    project_name character varying,
    funding_round character varying,
    current_stage_id integer,
    funding_sought character varying,
    healthcare_sector_id integer,
    company_offering text,
    project_metadata text,
    tags text,
    is_test boolean,
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    owner_id integer
);


ALTER TABLE public.projects OWNER TO review_user;

--
-- Name: project_progress; Type: VIEW; Schema: public; Owner: review_user
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


ALTER VIEW public.project_progress OWNER TO review_user;

--
-- Name: project_stages_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.project_stages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.project_stages_id_seq OWNER TO review_user;

--
-- Name: project_stages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.project_stages_id_seq OWNED BY public.project_stages.id;


--
-- Name: projects_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.projects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.projects_id_seq OWNER TO review_user;

--
-- Name: projects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.projects_id_seq OWNED BY public.projects.id;


--
-- Name: question_analysis_results; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.question_analysis_results (
    id integer NOT NULL,
    pitch_deck_id integer NOT NULL,
    question_id integer NOT NULL,
    raw_response text,
    structured_response text,
    score integer,
    confidence_score numeric,
    processing_time numeric,
    model_used character varying(100),
    prompt_used text,
    created_at timestamp without time zone
);


ALTER TABLE public.question_analysis_results OWNER TO review_user;

--
-- Name: question_analysis_results_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.question_analysis_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.question_analysis_results_id_seq OWNER TO review_user;

--
-- Name: question_analysis_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.question_analysis_results_id_seq OWNED BY public.question_analysis_results.id;


--
-- Name: questions; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.questions (
    id integer NOT NULL,
    review_id integer,
    question_text text,
    asked_by integer,
    created_at timestamp without time zone
);


ALTER TABLE public.questions OWNER TO review_user;

--
-- Name: questions_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.questions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.questions_id_seq OWNER TO review_user;

--
-- Name: questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.questions_id_seq OWNED BY public.questions.id;


--
-- Name: reviews; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.reviews (
    id integer NOT NULL,
    pitch_deck_id integer,
    review_data text,
    s3_review_url character varying,
    status character varying,
    created_at timestamp without time zone
);


ALTER TABLE public.reviews OWNER TO review_user;

--
-- Name: reviews_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.reviews_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reviews_id_seq OWNER TO review_user;

--
-- Name: reviews_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.reviews_id_seq OWNED BY public.reviews.id;


--
-- Name: slide_feedback; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.slide_feedback (
    id integer NOT NULL,
    pitch_deck_id integer NOT NULL,
    slide_number integer NOT NULL,
    slide_filename character varying(255) NOT NULL,
    feedback_text text,
    feedback_type character varying(50) DEFAULT 'ai_analysis'::character varying,
    has_issues boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.slide_feedback OWNER TO postgres;

--
-- Name: TABLE slide_feedback; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.slide_feedback IS 'Stores AI-generated feedback for individual slides in pitch decks';


--
-- Name: COLUMN slide_feedback.pitch_deck_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.slide_feedback.pitch_deck_id IS 'Reference to the pitch deck containing this slide';


--
-- Name: COLUMN slide_feedback.slide_number; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.slide_feedback.slide_number IS 'Sequential number of the slide within the deck (1-based)';


--
-- Name: COLUMN slide_feedback.slide_filename; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.slide_feedback.slide_filename IS 'Filename of the slide image (e.g., slide_001.png)';


--
-- Name: COLUMN slide_feedback.feedback_text; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.slide_feedback.feedback_text IS 'AI-generated feedback text, NULL if has_issues=false';


--
-- Name: COLUMN slide_feedback.feedback_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.slide_feedback.feedback_type IS 'Type of feedback: ai_analysis, human_review, etc.';


--
-- Name: COLUMN slide_feedback.has_issues; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.slide_feedback.has_issues IS 'TRUE if slide has issues requiring feedback, FALSE for "SLIDE_OK"';


--
-- Name: slide_feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.slide_feedback_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.slide_feedback_id_seq OWNER TO postgres;

--
-- Name: slide_feedback_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.slide_feedback_id_seq OWNED BY public.slide_feedback.id;


--
-- Name: specialized_analysis_results; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.specialized_analysis_results (
    id integer NOT NULL,
    pitch_deck_id integer NOT NULL,
    analysis_type character varying(100) NOT NULL,
    analysis_result text,
    structured_result text,
    confidence_score numeric,
    model_used character varying(100),
    processing_time numeric,
    created_at timestamp without time zone
);


ALTER TABLE public.specialized_analysis_results OWNER TO review_user;

--
-- Name: specialized_analysis_results_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.specialized_analysis_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.specialized_analysis_results_id_seq OWNER TO review_user;

--
-- Name: specialized_analysis_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.specialized_analysis_results_id_seq OWNED BY public.specialized_analysis_results.id;


--
-- Name: stage_templates; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.stage_templates (
    id integer NOT NULL,
    stage_name character varying(255) NOT NULL,
    stage_code character varying(100) NOT NULL,
    description text,
    stage_order integer NOT NULL,
    is_required boolean,
    estimated_duration_days integer,
    stage_metadata jsonb,
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.stage_templates OWNER TO review_user;

--
-- Name: stage_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.stage_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.stage_templates_id_seq OWNER TO review_user;

--
-- Name: stage_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.stage_templates_id_seq OWNED BY public.stage_templates.id;


--
-- Name: startup_classifications; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.startup_classifications (
    id integer NOT NULL,
    pitch_deck_id integer NOT NULL,
    company_offering text NOT NULL,
    primary_sector_id integer,
    subcategory character varying(255),
    confidence_score numeric,
    classification_reasoning text,
    secondary_sector_id integer,
    keywords_matched text,
    template_used integer,
    manual_override boolean,
    manual_override_reason text,
    classified_by character varying(255),
    created_at timestamp without time zone
);


ALTER TABLE public.startup_classifications OWNER TO review_user;

--
-- Name: startup_classifications_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.startup_classifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.startup_classifications_id_seq OWNER TO review_user;

--
-- Name: startup_classifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.startup_classifications_id_seq OWNED BY public.startup_classifications.id;


--
-- Name: task_dependencies; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.task_dependencies (
    id integer NOT NULL,
    dependent_task_id integer NOT NULL,
    depends_on_task_id integer NOT NULL,
    dependency_type character varying(50) DEFAULT 'completion'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.task_dependencies OWNER TO review_user;

--
-- Name: TABLE task_dependencies; Type: COMMENT; Schema: public; Owner: review_user
--

COMMENT ON TABLE public.task_dependencies IS 'Task dependency management for complex workflows';


--
-- Name: task_dependencies_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.task_dependencies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.task_dependencies_id_seq OWNER TO review_user;

--
-- Name: task_dependencies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.task_dependencies_id_seq OWNED BY public.task_dependencies.id;


--
-- Name: template_chapters; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.template_chapters (
    id integer NOT NULL,
    template_id integer NOT NULL,
    chapter_id character varying(100) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    weight numeric,
    order_index integer,
    is_required boolean,
    enabled boolean,
    chapter_prompt_template text,
    scoring_prompt_template text,
    created_at timestamp without time zone,
    modified_at timestamp without time zone,
    analysis_template_id integer
);


ALTER TABLE public.template_chapters OWNER TO review_user;

--
-- Name: template_chapters_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.template_chapters_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.template_chapters_id_seq OWNER TO review_user;

--
-- Name: template_chapters_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.template_chapters_id_seq OWNED BY public.template_chapters.id;


--
-- Name: template_configurations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.template_configurations (
    id integer NOT NULL,
    user_id integer NOT NULL,
    use_single_template boolean DEFAULT false,
    selected_template_id integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.template_configurations OWNER TO postgres;

--
-- Name: TABLE template_configurations; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.template_configurations IS 'Stores GP template processing preferences (single template mode vs classification mode)';


--
-- Name: COLUMN template_configurations.use_single_template; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.template_configurations.use_single_template IS 'When true, use selected_template_id for all analyses. When false, use classification.';


--
-- Name: COLUMN template_configurations.selected_template_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.template_configurations.selected_template_id IS 'Template to use when use_single_template is true';


--
-- Name: template_configurations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.template_configurations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.template_configurations_id_seq OWNER TO postgres;

--
-- Name: template_configurations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.template_configurations_id_seq OWNED BY public.template_configurations.id;


--
-- Name: template_performance; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.template_performance (
    id integer NOT NULL,
    template_id integer NOT NULL,
    pitch_deck_id integer NOT NULL,
    total_processing_time numeric,
    successful_questions integer,
    failed_questions integer,
    average_confidence numeric,
    gp_rating integer,
    gp_feedback text,
    created_at timestamp without time zone
);


ALTER TABLE public.template_performance OWNER TO review_user;

--
-- Name: template_performance_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.template_performance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.template_performance_id_seq OWNER TO review_user;

--
-- Name: template_performance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.template_performance_id_seq OWNED BY public.template_performance.id;


--
-- Name: test_projects; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.test_projects (
    id integer NOT NULL,
    company_id character varying(255),
    project_name character varying(255),
    funding_round character varying(100),
    current_stage_id integer,
    funding_sought text,
    healthcare_sector_id integer,
    company_offering text,
    project_metadata jsonb,
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    tags jsonb,
    is_test boolean
);


ALTER TABLE public.test_projects OWNER TO review_user;

--
-- Name: test_projects_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.test_projects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.test_projects_id_seq OWNER TO review_user;

--
-- Name: test_projects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.test_projects_id_seq OWNED BY public.test_projects.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: review_user
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
    last_name character varying,
    must_change_password boolean DEFAULT false
);


ALTER TABLE public.users OWNER TO review_user;

--
-- Name: COLUMN users.must_change_password; Type: COMMENT; Schema: public; Owner: review_user
--

COMMENT ON COLUMN public.users.must_change_password IS 'Forces user to change password on next login - used for invited users';


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO review_user;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: visual_analysis_cache; Type: TABLE; Schema: public; Owner: review_user
--

CREATE TABLE public.visual_analysis_cache (
    id integer NOT NULL,
    pitch_deck_id integer NOT NULL,
    analysis_result_json text NOT NULL,
    vision_model_used character varying(255) NOT NULL,
    prompt_used text NOT NULL,
    created_at timestamp without time zone
);


ALTER TABLE public.visual_analysis_cache OWNER TO review_user;

--
-- Name: visual_analysis_cache_id_seq; Type: SEQUENCE; Schema: public; Owner: review_user
--

CREATE SEQUENCE public.visual_analysis_cache_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.visual_analysis_cache_id_seq OWNER TO review_user;

--
-- Name: visual_analysis_cache_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: review_user
--

ALTER SEQUENCE public.visual_analysis_cache_id_seq OWNED BY public.visual_analysis_cache.id;


--
-- Name: analysis_templates id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.analysis_templates ALTER COLUMN id SET DEFAULT nextval('public.analysis_templates_id_seq'::regclass);


--
-- Name: answers id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.answers ALTER COLUMN id SET DEFAULT nextval('public.answers_id_seq'::regclass);


--
-- Name: chapter_analysis_results id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.chapter_analysis_results ALTER COLUMN id SET DEFAULT nextval('public.chapter_analysis_results_id_seq'::regclass);


--
-- Name: chapter_questions id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.chapter_questions ALTER COLUMN id SET DEFAULT nextval('public.chapter_questions_id_seq'::regclass);


--
-- Name: classification_performance id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.classification_performance ALTER COLUMN id SET DEFAULT nextval('public.classification_performance_id_seq'::regclass);


--
-- Name: extraction_experiments id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.extraction_experiments ALTER COLUMN id SET DEFAULT nextval('public.extraction_experiments_id_seq'::regclass);


--
-- Name: gp_template_customizations id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.gp_template_customizations ALTER COLUMN id SET DEFAULT nextval('public.gp_template_customizations_id_seq'::regclass);


--
-- Name: healthcare_sectors id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.healthcare_sectors ALTER COLUMN id SET DEFAULT nextval('public.healthcare_sectors_id_seq'::regclass);


--
-- Name: healthcare_templates_deprecated id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.healthcare_templates_deprecated ALTER COLUMN id SET DEFAULT nextval('public.healthcare_templates_deprecated_id_seq'::regclass);


--
-- Name: model_configs id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.model_configs ALTER COLUMN id SET DEFAULT nextval('public.model_configs_id_seq'::regclass);


--
-- Name: pipeline_prompts id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pipeline_prompts ALTER COLUMN id SET DEFAULT nextval('public.pipeline_prompts_id_seq'::regclass);


--
-- Name: pitch_decks id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.pitch_decks ALTER COLUMN id SET DEFAULT nextval('public.pitch_decks_id_seq'::regclass);


--
-- Name: processing_progress id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.processing_progress ALTER COLUMN id SET DEFAULT nextval('public.processing_progress_id_seq'::regclass);


--
-- Name: processing_queue id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.processing_queue ALTER COLUMN id SET DEFAULT nextval('public.processing_queue_id_seq'::regclass);


--
-- Name: production_projects id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.production_projects ALTER COLUMN id SET DEFAULT nextval('public.production_projects_id_seq'::regclass);


--
-- Name: project_documents id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.project_documents ALTER COLUMN id SET DEFAULT nextval('public.project_documents_id_seq'::regclass);


--
-- Name: project_interactions id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.project_interactions ALTER COLUMN id SET DEFAULT nextval('public.project_interactions_id_seq'::regclass);


--
-- Name: project_invitations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_invitations ALTER COLUMN id SET DEFAULT nextval('public.project_invitations_id_seq'::regclass);


--
-- Name: project_members id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_members ALTER COLUMN id SET DEFAULT nextval('public.project_members_id_seq'::regclass);


--
-- Name: project_stages id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.project_stages ALTER COLUMN id SET DEFAULT nextval('public.project_stages_id_seq'::regclass);


--
-- Name: projects id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.projects ALTER COLUMN id SET DEFAULT nextval('public.projects_id_seq'::regclass);


--
-- Name: question_analysis_results id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.question_analysis_results ALTER COLUMN id SET DEFAULT nextval('public.question_analysis_results_id_seq'::regclass);


--
-- Name: questions id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.questions ALTER COLUMN id SET DEFAULT nextval('public.questions_id_seq'::regclass);


--
-- Name: reviews id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.reviews ALTER COLUMN id SET DEFAULT nextval('public.reviews_id_seq'::regclass);


--
-- Name: slide_feedback id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.slide_feedback ALTER COLUMN id SET DEFAULT nextval('public.slide_feedback_id_seq'::regclass);


--
-- Name: specialized_analysis_results id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.specialized_analysis_results ALTER COLUMN id SET DEFAULT nextval('public.specialized_analysis_results_id_seq'::regclass);


--
-- Name: stage_templates id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.stage_templates ALTER COLUMN id SET DEFAULT nextval('public.stage_templates_id_seq'::regclass);


--
-- Name: startup_classifications id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.startup_classifications ALTER COLUMN id SET DEFAULT nextval('public.startup_classifications_id_seq'::regclass);


--
-- Name: task_dependencies id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.task_dependencies ALTER COLUMN id SET DEFAULT nextval('public.task_dependencies_id_seq'::regclass);


--
-- Name: template_chapters id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.template_chapters ALTER COLUMN id SET DEFAULT nextval('public.template_chapters_id_seq'::regclass);


--
-- Name: template_configurations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.template_configurations ALTER COLUMN id SET DEFAULT nextval('public.template_configurations_id_seq'::regclass);


--
-- Name: template_performance id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.template_performance ALTER COLUMN id SET DEFAULT nextval('public.template_performance_id_seq'::regclass);


--
-- Name: test_projects id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.test_projects ALTER COLUMN id SET DEFAULT nextval('public.test_projects_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: visual_analysis_cache id; Type: DEFAULT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.visual_analysis_cache ALTER COLUMN id SET DEFAULT nextval('public.visual_analysis_cache_id_seq'::regclass);


--
-- Data for Name: analysis_templates; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.analysis_templates (id, healthcare_sector_id, name, description, template_version, specialized_analysis, is_active, is_default, usage_count, created_by, created_at, modified_at, analysis_prompt) FROM stdin;
9	1	Standard Seven-Chapter Review	The standard seven-chapter review template used for comprehensive startup analysis	1.0	["problem_analysis", "solution_approach", "product_market_fit", "monetization", "financials", "use_of_funds", "organization"]	t	f	0	\N	\N	\N	\N
5	5	Biotech & Pharma Standard Analysis	Analysis template for biotech and pharmaceutical companies	v1.0	["scientific_hypothesis", "clinical_strategy", "regulatory_timeline", "ip_position"]	t	t	0	\N	\N	\N	\N
1	1	Digital Therapeutics Standard Analysis	Comprehensive analysis template for digital therapeutics and mental health startups	v1.0	["clinical_validation", "regulatory_pathway", "patient_outcomes", "engagement_metrics"]	t	t	0	\N	\N	\N	\N
2	2	Healthcare Infrastructure Standard Analysis	Analysis template for healthcare IT infrastructure and workflow solutions	v1.0	["integration_analysis", "workflow_impact", "roi_calculation", "adoption_barriers"]	t	t	0	\N	\N	\N	\N
3	3	Telemedicine Standard Analysis	Analysis template for telemedicine and remote care platforms	v1.0	["care_quality", "patient_satisfaction", "provider_workflow", "technology_infrastructure"]	t	t	0	\N	\N	\N	\N
4	4	Diagnostics & Devices Standard Analysis	Analysis template for diagnostic tools and medical devices	v1.0	["clinical_accuracy", "regulatory_pathway", "manufacturing_quality", "market_access"]	t	t	0	\N	\N	\N	\N
6	6	Health Data & AI Standard Analysis	Analysis template for health data and AI companies	v1.0	["ai_validation", "data_quality", "clinical_integration", "algorithm_performance"]	t	t	0	\N	\N	\N	\N
7	7	Consumer Health Standard Analysis	Analysis template for consumer health and wellness companies	v1.0	["user_engagement", "behavior_change", "monetization_strategy", "market_differentiation"]	t	t	0	\N	\N	\N	\N
8	8	Healthcare Marketplaces Standard Analysis	Analysis template for healthcare marketplaces and access platforms	v1.0	["network_effects", "market_dynamics", "regulatory_compliance", "scalability_analysis"]	t	t	0	\N	\N	\N	\N
\.


--
-- Data for Name: answers; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.answers (id, question_id, answer_text, answered_by, created_at) FROM stdin;
\.


--
-- Data for Name: chapter_analysis_results; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.chapter_analysis_results (id, pitch_deck_id, chapter_id, chapter_response, average_score, weighted_score, total_questions, answered_questions, processing_time, created_at) FROM stdin;
\.


--
-- Data for Name: chapter_questions; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.chapter_questions (id, chapter_id, question_id, question_text, weight, order_index, enabled, scoring_criteria, healthcare_focus, question_prompt_template, created_at, modified_at) FROM stdin;
1	1	problem_who	Who has the problem?	1.0	1	t	Score based on clarity of target audience identification (1-5 scale)	general	\N	\N	\N
2	1	problem_nature	What exactly is the nature of the problem?	1.0	2	t	Score based on problem definition clarity and specificity (1-5 scale)	general	\N	\N	\N
3	1	problem_pain_points	What are the pain points?	1.0	3	t	Score based on depth of pain point analysis (1-5 scale)	general	\N	\N	\N
4	1	problem_quantification	Can the problem be quantified?	1.0	4	t	Score based on data-driven problem validation (1-5 scale)	general	\N	\N	\N
5	2	solution_description	What exactly does your solution look like?	1.0	1	t	Score based on solution clarity and innovation (1-5 scale)	general	\N	\N	\N
6	2	solution_differentiation	What distinguishes it from existing solutions?	1.0	2	t	Score based on competitive differentiation strength (1-5 scale)	general	\N	\N	\N
7	2	solution_competitors	Are there competitors and what does their solution look like?	1.0	3	t	Score based on competitive landscape understanding (1-5 scale)	general	\N	\N	\N
8	2	solution_advantage	Can you quantify your advantage?	1.0	4	t	Score based on measurable competitive advantages (1-5 scale)	general	\N	\N	\N
9	3	pmf_customers	Do you have paying customers or convinced pilot customers?	1.0	1	t	Score based on customer traction evidence (1-5 scale)	general	\N	\N	\N
10	3	pmf_discovery	How did you find them?	1.0	2	t	Score based on customer acquisition strategy (1-5 scale)	general	\N	\N	\N
11	3	pmf_satisfaction	What do users & payers love about your solution?	1.0	3	t	Score based on customer satisfaction evidence (1-5 scale)	general	\N	\N	\N
12	3	pmf_churn	What is the churn and the reasons for it?	1.0	4	t	Score based on retention metrics and analysis (1-5 scale)	general	\N	\N	\N
13	4	monetization_payer	Who will pay for it?	1.0	1	t	Score based on payer identification clarity (1-5 scale)	general	\N	\N	\N
14	4	monetization_decision	What does the buyer's decision-making structure look like?	1.0	2	t	Score based on sales process understanding (1-5 scale)	general	\N	\N	\N
15	4	monetization_pricing	How did you design the pricing and why exactly like this?	1.0	3	t	Score based on pricing strategy rationale (1-5 scale)	general	\N	\N	\N
16	4	monetization_economics	What are your margins, what are the unit economics?	1.0	4	t	Score based on unit economics clarity (1-5 scale)	general	\N	\N	\N
17	5	financials_burn	What is your current monthly burn?	1.0	1	t	Score based on financial transparency and planning (1-5 scale)	general	\N	\N	\N
18	5	financials_sales	What are your monthly sales?	1.0	2	t	Score based on revenue visibility and growth (1-5 scale)	general	\N	\N	\N
19	5	financials_fluctuations	Are there any major fluctuations? If so, why?	1.0	3	t	Score based on financial stability understanding (1-5 scale)	general	\N	\N	\N
20	5	financials_funding	How much funding are you looking for, why exactly this amount?	1.0	4	t	Score based on funding requirement justification (1-5 scale)	general	\N	\N	\N
21	6	funds_allocation	What will you do with the money?	1.0	1	t	Score based on fund allocation clarity (1-5 scale)	general	\N	\N	\N
22	6	funds_priorities	Is there a ranked list of deficits that you want to address?	1.0	2	t	Score based on strategic prioritization (1-5 scale)	general	\N	\N	\N
23	6	funds_strategy	Can you tell us about your investment strategy?	1.0	3	t	Score based on strategic thinking depth (1-5 scale)	general	\N	\N	\N
24	6	funds_future	What will your company look like at the end of this investment period?	1.0	4	t	Score based on future vision clarity (1-5 scale)	general	\N	\N	\N
25	7	org_team	Who are you, what experience do you have?	1.0	1	t	Score based on team experience relevance (1-5 scale)	general	\N	\N	\N
26	7	org_maturity	How can your organizational maturity be described?	1.0	2	t	Score based on organizational development level (1-5 scale)	general	\N	\N	\N
27	7	org_structure	How many people are you / pie chart of people per unit?	1.0	3	t	Score based on team structure appropriateness (1-5 scale)	general	\N	\N	\N
28	7	org_gaps	What skills are missing in the management team?	1.0	4	t	Score based on skill gap awareness and planning (1-5 scale)	general	\N	\N	\N
29	8	question_1	q1	1.0	0	t		\N	\N	\N	\N
\.


--
-- Data for Name: classification_performance; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.classification_performance (id, classification_id, was_accurate, manual_correction_from, manual_correction_to, correction_reason, corrected_by, created_at) FROM stdin;
\.


--
-- Data for Name: extraction_experiments; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.extraction_experiments (id, experiment_name, pitch_deck_ids, extraction_type, text_model_used, extraction_prompt, results_json, created_at, classification_enabled, classification_results_json, classification_completed_at, company_name_results_json, company_name_completed_at, funding_amount_results_json, funding_amount_completed_at, deck_date_results_json, deck_date_completed_at, template_processing_results_json, classification_model_used, template_processing_completed_at) FROM stdin;
10	pipeline_1754218360807	{119}	company_offering	phi4:latest	Your task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company. Please do not write any introductory sentences and do not repeat the instruction, just provide what you are asked for.	{"experiment_name": "pipeline_1754218360807", "extraction_type": "company_offering", "text_model_used": "phi4:latest", "extraction_prompt": "Your task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company. Please do not write any introductory sentences and do not repeat the instruction, just provide what you are asked for.", "results": [{"deck_id": 119, "offering_extraction": "A wearable device that monitors infants' vital signs, such as heart rate and oxygen saturation, providing data to parents through a mobile app interface.", "text_model_used": "phi4:latest", "visual_analysis_used": true, "filename": "2025_Lilio Investment Deck.pdf"}], "total_decks": 1, "successful_extractions": 1, "created_at": "2025-08-03T10:52:45.029095"}	2025-08-03 10:52:40.879717	t	{"classification_results": [{"deck_id": 119, "filename": "2025_Lilio Investment Deck.pdf", "company_offering": "A wearable device that monitors infants' vital signs, such as heart rate and oxygen saturation, providing data to parents through a mobile app interface.", "classification": {"primary_sector": "diagnostics_devices", "subcategory": "Wearable Health Monitors", "confidence_score": 0.95, "reasoning": "The company's offering \\u2013 a wearable device monitoring infant vital signs and providing data to parents via a mobile app \\u2013 directly aligns with the definition of Diagnostics & Medical Devices, specifically within the Wearable Health Monitors subcategory. The core business is providing a device for health monitoring, a key characteristic of this sector. The target market is parents of infants, and the solution is a physical device providing physiological data. While there's a mobile app component, the primary value proposition is the wearable device itself. The keyword analysis confirms the 'wearable' aspect. The focus is on providing diagnostic information, albeit in a consumer-facing manner.", "secondary_sector": "Consumer Health & Wellness", "keywords_matched": ["wearable", "monitoring", "vital signs", "mobile app"], "recommended_template": 4}, "confidence_score": 0.95, "primary_sector": "diagnostics_devices", "secondary_sector": "Consumer Health & Wellness", "keywords_matched": ["wearable", "monitoring", "vital signs", "mobile app"], "reasoning": "The company's offering \\u2013 a wearable device monitoring infant vital signs and providing data to parents via a mobile app \\u2013 directly aligns with the definition of Diagnostics & Medical Devices, specifically within the Wearable Health Monitors subcategory. The core business is providing a device for health monitoring, a key characteristic of this sector. The target market is parents of infants, and the solution is a physical device providing physiological data. While there's a mobile app component, the primary value proposition is the wearable device itself. The keyword analysis confirms the 'wearable' aspect. The focus is on providing diagnostic information, albeit in a consumer-facing manner.", "error": null}], "classification_by_deck": {"119": {"primary_sector": "diagnostics_devices", "secondary_sector": "Consumer Health & Wellness", "confidence_score": 0.95, "reasoning": "The company's offering \\u2013 a wearable device monitoring infant vital signs and providing data to parents via a mobile app \\u2013 directly aligns with the definition of Diagnostics & Medical Devices, specifically within the Wearable Health Monitors subcategory. The core business is providing a device for health monitoring, a key characteristic of this sector. The target market is parents of infants, and the solution is a physical device providing physiological data. While there's a mobile app component, the primary value proposition is the wearable device itself. The keyword analysis confirms the 'wearable' aspect. The focus is on providing diagnostic information, albeit in a consumer-facing manner.", "keywords_matched": ["wearable", "monitoring", "vital signs", "mobile app"], "classification_error": null}}, "statistics": {"total_decks": 1, "successful_classifications": 1, "failed_classifications": 0, "success_rate": 1.0, "average_confidence": 0.95, "sector_distribution": {"diagnostics_devices": 1}}, "model_used": "gemma3:12b", "classified_at": "2025-08-03T10:52:52.257607"}	2025-08-03 10:52:45.091486	{"company_name_results": [{"deck_id": 119, "filename": "deck_119", "company_name": "Lilio", "error": null}], "statistics": {"total_decks": 1, "successful_extractions": 1, "failed_extractions": 0, "success_rate": 1.0}, "model_used": "phi4:latest", "prompt_used": "Please find the name of the startup in the pitchdeck. Deliver only the name, no conversational text around it.", "extracted_at": "2025-08-03T10:52:53.172296"}	2025-08-03 10:52:52.320706	{"funding_amount_results": [{"deck_id": 119, "filename": "deck_119", "funding_amount": "Not specified\\n\\nThe visual analysis provided does not mention any specific funding amount that the startup is seeking. There are no phrases like 'seeking \\u20acX', 'raising $X', or similar in the descriptions of the slides. Therefore, based on the information given, it cannot be determined what specific funding amount is being sought by the startup.", "error": null}], "statistics": {"total_decks": 1, "successful_extractions": 1, "failed_extractions": 0, "success_rate": 1.0}, "model_used": "phi4:latest", "prompt_used": "Please extract the specific funding amount the startup is seeking from the pitch deck. Look for phrases like 'seeking \\u20acX', 'raising $X', 'funding requirement of X', or similar. If you find multiple amounts (seed, Series A, total, etc.), focus on the primary funding amount being sought in this round. Provide only the amount (e.g., '\\u20ac2.5M', '$500K', '\\u00a31M') without additional explanation. If no specific amount is mentioned, respond with 'Not specified'.", "extracted_at": "2025-08-03T10:52:54.986916"}	2025-08-03 10:52:53.232555	{"deck_date_results": [{"deck_id": 119, "filename": "deck_119", "deck_date": "Based on the pitch deck visual analysis provided, there are two instances where date information can be found:\\n\\n1. **Page 11**: The slide includes a footer at the bottom that contains a timestamp and a reference number. This suggests that it is likely to provide the most recent update or creation date for this version of the pitch deck.\\n\\n2. **Page 8**: While not explicitly stated as a date, this page mentions financial projections for the years 2024 and 2026, indicating that the content was prepared with these future dates in mind.\\n\\nGiven the context, the timestamp on Page 11 is the most direct indicator of when the pitch deck was last updated or created. However, since the exact format of the date from the timestamp isn't provided in the analysis, we can only confirm that it exists there without specifying the precise date.\\n\\nTherefore, based on the visual analysis:\\n\\n- **Most Recent Date Indicated**: The timestamp on Page 11 suggests a recent update, but the specific date is not detailed here.\\n- If you need the exact format of this date, you would need to refer directly to the slide itself for that information. \\n\\nIn conclusion, while we know there's a timestamp indicating when it was last updated, without seeing the actual slide, I can't provide an explicit date in a specific format like 'March 2024', '2024-03-15', or 'Q1 2024'.", "error": null}], "statistics": {"total_decks": 1, "successful_extractions": 1, "failed_extractions": 0, "success_rate": 1.0}, "model_used": "phi4:latest", "prompt_used": "Please identify when this pitch deck was created or last updated. Look for dates in headers, footers, slide timestamps, version information, or any date references that indicate when the deck was prepared. Focus on the most recent date that reflects when the current version was created. Provide the date in a clear format (e.g., 'March 2024', '2024-03-15', 'Q1 2024'). If no date information is available, respond with 'Date not found'.", "extracted_at": "2025-08-03T10:52:59.859407"}	2025-08-03 10:52:55.048028	{"results": [{"deck_id": 119, "chapters": {"Problem Analysis": {"name": "Problem Analysis", "key": "problem_analysis", "description": "Analysis of the problem being addressed by the startup", "questions": [{"id": 1, "question_id": "problem_who", "question_text": "Who has the problem?", "response": "Based on the pitch deck content, the primary problem addressed is related to infant health monitoring. The target users are parents who need reliable tools for ensuring their child's well-being during critical periods such as sleep and daily activities. This demographic faces challenges in obtaining real-time data about vital signs like heart rate and oxygen saturation without intrusive or cumbersome devices.\\n\\nThe pitch deck emphasizes a solution that integrates seamlessly into the lives of caregivers, offering peace of mind through non-invasive monitoring technology. The wearable device for infants is designed to provide continuous health tracking with an intuitive mobile interface, allowing parents to monitor their child's vital signs effortlessly. This addresses concerns about sudden infant conditions and empowers parents by providing them with actionable insights.\\n\\nThe emotional resonance highlighted in the deck suggests that beyond technical functionality, there is a significant focus on alleviating parental anxiety through reassurance of safety (\\"Calm & Safe\\") and confidence in managing their child\\u2019s health needs (\\"Empowered & Confident\\"). The product aims to offer a holistic approach by connecting various aspects of infant care into one cohesive system.\\n\\nOverall, the problem lies at the intersection of healthcare technology and family dynamics, where there is a demand for innovative solutions that enhance parental awareness and response capabilities regarding infant health.", "score": 6, "scoring_criteria": "Score based on clarity of target audience identification (1-5 scale)", "healthcare_focus": "general", "scoring_response": "6\\n\\nThis analysis provides clear identification of the target audience, which is parents concerned with infant health monitoring. The pitch deck effectively communicates that these users need non-intrusive devices for real-time data about vital signs like heart rate and oxygen saturation. It also highlights emotional aspects such as alleviating parental anxiety and empowering caregivers.\\n\\nThe presentation includes specific details on how the product addresses these needs, emphasizing ease of use and integration into daily routines through a wearable device with an intuitive mobile interface. The focus is well-aligned with healthcare-specific requirements by addressing both technical functionality and emotional reassurance for parents.\\n\\nWhile there are some gaps in clinical validation specifics within this analysis response, the overall clarity regarding who has the problem and how they will benefit from the solution is comprehensive and well-supported. Therefore, a score of 6 reflects an excellent level of audience identification with minor areas that could be further elaborated upon."}, {"id": 2, "question_id": "problem_nature", "question_text": "What exactly is the nature of the problem?", "response": "The problem addressed by the company revolves around enhancing infant care through advanced monitoring technology. The pitch deck highlights concerns related to ensuring infants' safety, comfort, and health during critical periods such as sleep. By leveraging wearable devices that track vital signs like heart rate and oxygen saturation, the solution aims to provide parents with real-time data on their child's well-being. This approach addresses a significant gap in traditional infant care methods by offering continuous monitoring capabilities that can alert caregivers to potential issues before they escalate into emergencies.\\n\\nThe clinical relevance of this problem is underscored by the need for non-invasive and reliable health metrics, which are crucial during infancy when children are most vulnerable. The pitch deck emphasizes ease of use and integration with daily routines, suggesting a design focused on minimizing disruption while maximizing peace of mind for parents. By positioning their product as both innovative and user-friendly, the company seeks to empower caregivers with actionable insights into their child's health status.\\n\\nFurthermore, the emotional aspect is highlighted through imagery that evokes feelings of calmness and safety, reinforcing the importance of trust in healthcare solutions. The competitive landscape analysis indicates a market ripe for differentiation, particularly through features like patent-pending technology and holistic monitoring capabilities. Overall, the company aims to transform infant care by bridging gaps between wellness practices and advanced health monitoring technologies, ultimately contributing to a broader healthcare revolution focused on proactive rather than reactive measures.", "score": 6, "scoring_criteria": "Score based on problem definition clarity and specificity (1-5 scale)", "healthcare_focus": "general", "scoring_response": "6\\n\\nThis analysis provides a clear and specific definition of the problem, focusing on enhancing infant care through advanced monitoring technology. The pitch deck effectively highlights concerns related to infants' safety, comfort, and health during critical periods such as sleep. It addresses gaps in traditional methods by offering continuous monitoring capabilities that can alert caregivers to potential issues before they escalate into emergencies.\\n\\nThe response also emphasizes clinical relevance with non-invasive and reliable health metrics crucial for infant care. The emotional aspect is well-covered through imagery evoking feelings of calmness and safety, reinforcing trust in healthcare solutions. Additionally, the competitive landscape analysis indicates a market ripe for differentiation, particularly through patent-pending technology and holistic monitoring capabilities.\\n\\nOverall, the problem definition is comprehensive and well-supported, aligning with healthcare-specific requirements and clinical validation needs."}, {"id": 3, "question_id": "problem_pain_points", "question_text": "What are the pain points?", "response": "The pitch deck highlights several pain points in the general healthcare sector, particularly focusing on infant care. The primary issues revolve around ensuring infants' safety and well-being through continuous monitoring. Parents face anxiety regarding sudden health changes in their babies, such as temperature fluctuations or oxygen saturation levels, which can be critical indicators of distress or illness. Current solutions may lack integration into daily routines, causing inconvenience or requiring constant attention from caregivers.\\n\\nThe product aims to address these concerns by offering a wearable device that provides real-time data on vital signs like heart rate and body temperature in an intuitive mobile interface. This solution emphasizes ease of use and emotional reassurance for parents, allowing them to monitor their child's health seamlessly without disrupting daily activities. The minimalist design suggests a focus on user experience, aiming to reduce parental stress by offering reliable, connected monitoring that empowers caregivers with confidence and peace of mind.\\n\\nAdditionally, the competitive landscape analysis indicates gaps in existing products regarding comfort, size, and technological sophistication. By positioning itself as a \\"patent-pending\\" solution, the company seeks to differentiate its product through advanced features like comprehensive health diaries and audio feedback, addressing both technical and emotional needs of parents seeking holistic care for their infants.\\n\\nOverall, the pitch deck underscores the need for innovative solutions that integrate seamlessly into family life while providing reliable data to alleviate parental concerns about infant health.", "score": 4, "scoring_criteria": "Score based on depth of pain point analysis (1-5 scale)", "healthcare_focus": "general", "scoring_response": "4\\n\\nThis analysis provides an adequate depth in identifying pain points within the healthcare sector, specifically focusing on infant care. It effectively highlights key issues such as parental anxiety over sudden health changes in infants and the inconvenience of current monitoring solutions. The response also outlines how the proposed product aims to address these concerns through real-time data integration into daily routines.\\n\\nHowever, while it mentions gaps in existing products regarding comfort, size, and technological sophistication, there is limited exploration of broader systemic issues or clinical validation needs that could further enrich the pain point analysis. Additionally, more detailed insights into specific challenges faced by healthcare providers or caregivers would enhance the depth of understanding.\\n\\nOverall, the response demonstrates a good grasp of primary consumer concerns but lacks some comprehensive coverage of potential industry-wide implications and deeper technical validations."}, {"id": 4, "question_id": "problem_quantification", "question_text": "Can the problem be quantified?", "response": "Based on the pitch deck content provided, it appears that while there is some quantifiable data presented in terms of financial projections for hardware, app revenue, and subscription services (with specific figures given for 2024 and 2026), the problem itself\\u2014related to infant monitoring\\u2014is not explicitly quantified. The slides focus more on user experience, emotional resonance, and competitive positioning rather than providing concrete statistics or metrics that define the scale of the issue being addressed.\\n\\nThe pitch emphasizes design elements such as ease of use and integration into daily routines, suggesting a qualitative approach to problem-solving. Additionally, while there is mention of market sizing data (TAM, SAM, SOM), these figures are not directly tied back to specific problems within infant care or monitoring that need addressing. The competitive landscape analysis provides context but does not quantify the extent of any gaps in current solutions.\\n\\nFor healthcare-specific considerations and clinical relevance, it would be beneficial for the pitch deck to include data on incidence rates of issues like Sudden Infant Death Syndrome (SIDS), common sleep disturbances among infants, or other health metrics that could justify the need for such a monitoring solution. This quantification would strengthen the case by linking the product directly to measurable healthcare challenges.\\n\\nIn summary, while there are financial projections and market sizing data available in the pitch deck, these do not fully quantify the problem being addressed from a clinical perspective. More detailed statistics or studies related to infant health issues could enhance the presentation's effectiveness for investors focused on healthcare innovation.", "score": 4, "scoring_criteria": "Score based on data-driven problem validation (1-5 scale)", "healthcare_focus": "general", "scoring_response": "4\\n\\nThis score reflects that the pitch deck provides some quantifiable data, particularly in financial projections for hardware, app revenue, and subscription services. However, it lacks specific statistics or metrics directly related to the clinical problem of infant monitoring, such as incidence rates of SIDS or common sleep disturbances among infants. While market sizing data is included, it does not explicitly quantify the healthcare issue being addressed. Therefore, while there are adequate financial projections, more detailed and clinically relevant quantification would enhance the pitch's effectiveness for investors focused on healthcare innovation."}], "weighted_score": 5.0, "average_score": 5.0, "total_questions": 4, "code_version": "v2.0-with-questions-array"}, "Solution Approach": {"name": "Solution Approach", "key": "solution_approach", "description": "Analysis of the proposed solution and competitive differentiation", "questions": [{"id": 5, "question_id": "solution_description", "question_text": "What exactly does your solution look like?", "response": "The solution presented in the pitch deck is an innovative infant monitoring system designed for seamless integration into daily life, focusing on ease of use and emotional resonance. The core component is a wearable device worn by infants that communicates with a mobile application via a base station. This setup provides real-time data such as heart rate, oxygen saturation, temperature, and comfort levels, displayed in an intuitive interface. The system emphasizes user experience through its minimalist design, aiming to empower parents with reliable monitoring while maintaining the child's safety and well-being.\\n\\nThe product is positioned within a competitive landscape alongside existing solutions like Owlet Smart Sock and NeeBo Sensor Bracelet but distinguishes itself by offering patent-pending technology that promises enhanced comfort and comprehensive data tracking. The solution also integrates holistic features, such as audio diaries for capturing infant sounds, which contribute to its unique value proposition.\\n\\nFinancial projections indicate significant growth potential, with revenue streams from hardware sales, a basic app, and premium subscription services expected to increase substantially by 2026. This reflects confidence in the product's market acceptance and scalability.\\n\\nOverall, the solution is designed not only as a technological advancement but also as an emotionally supportive tool for parents, aligning with themes of calmness, safety, empowerment, reliability, holistic care, and connectivity. The brand aims to revolutionize infant monitoring by transitioning from wellness-focused solutions to comprehensive healthcare support systems.", "score": 6, "scoring_criteria": "Score based on solution clarity and innovation (1-5 scale)", "healthcare_focus": "general", "scoring_response": "6\\n\\nThis pitch deck provides comprehensive information about the solution, including its innovative aspects such as patent-pending technology for enhanced comfort and data tracking. The integration with mobile applications and emphasis on user experience through minimalist design are well-articulated. Additionally, it distinguishes itself from competitors by offering unique features like audio diaries.\\n\\nThe financial projections indicate a clear growth strategy, which adds to the solution's credibility. However, while there is mention of clinical validation needs in terms of safety and reliability, specific details on regulatory compliance or clinical trials are not explicitly covered, leaving some gaps for healthcare-specific requirements.\\n\\nOverall, the pitch deck effectively communicates its value proposition with clarity and innovation, warranting a high score but slightly reduced due to missing detailed information on clinical validation."}, {"id": 6, "question_id": "solution_differentiation", "question_text": "What distinguishes it from existing solutions?", "response": "Lilio distinguishes itself from existing solutions in the infant monitoring market through its innovative integration of technology, design, and user experience. Unlike competitors like Owlet Smart Sock and NeeBo Sensor Bracelet, Lilio's wearable device offers a comprehensive suite of features including oxygen saturation, heart rate, comfort levels, diaries, and audio monitoring, all encapsulated in patent-pending technology that emphasizes ease of use and emotional resonance with caregivers. The product is designed to seamlessly integrate into daily routines, providing real-time data through an intuitive mobile interface while maintaining a minimalist aesthetic that prioritizes the user experience. Lilio's approach not only focuses on technical capabilities but also aims to empower parents by offering reliable, holistic monitoring solutions that foster calmness and confidence in caregiving environments. This combination of advanced technology with empathetic design sets Lilio apart as it transitions from wellness-focused applications towards a broader healthcare revolution, positioning itself uniquely within the market landscape.", "score": 6, "scoring_criteria": "Score based on competitive differentiation strength (1-5 scale)", "healthcare_focus": "general", "scoring_response": "6\\n\\nThis response provides comprehensive information about Lilio's competitive differentiation, highlighting its unique features such as the integration of multiple monitoring capabilities (oxygen saturation, heart rate, comfort levels, diaries, and audio) in a patent-pending technology. It emphasizes ease of use, emotional resonance with caregivers, and seamless daily routine integration through an intuitive mobile interface. The analysis also contrasts Lilio's approach to competitors like Owlet Smart Sock and NeeBo Sensor Bracelet by focusing on holistic monitoring solutions that empower parents.\\n\\nThe response effectively communicates how these features set Lilio apart in the market landscape, transitioning from wellness-focused applications towards a broader healthcare revolution. It aligns well with healthcare-specific requirements by addressing both technical capabilities and user experience design, although it could further elaborate on clinical validation needs to achieve an even higher score. Overall, the information is detailed and supports Lilio's differentiation strategy effectively."}, {"id": 7, "question_id": "solution_competitors", "question_text": "Are there competitors and what does their solution look like?", "response": "In the competitive landscape for infant monitoring solutions, several key players are identified. The Owlet Smart Sock is designed primarily for sudden infant alerting, focusing on critical alerts that can notify parents of immediate concerns regarding an infant's well-being. Meanwhile, NeeBo offers a Sensor Bracelet touted as the smallest and most comfortable option available in the market, emphasizing user comfort and discreet monitoring capabilities. Lilio differentiates itself with its patent-pending technology integrated into their bracelet design, likely offering unique features or enhanced functionality compared to existing solutions.\\n\\nThese competitors highlight varying focal points: Owlet emphasizes safety through alerting mechanisms; NeeBo prioritizes physical comfort and minimal intrusion for the infant; and Lilio leverages innovative technology to potentially offer advanced monitoring capabilities. The presence of these established products suggests a market that values both technological innovation and user-centric design, indicating areas where new entrants must differentiate themselves either by enhancing existing features or introducing novel functionalities.\\n\\nThe pitch deck's emphasis on ease of use, emotional resonance, and integration into daily routines aligns with the competitive offerings but seeks to carve out its niche through a holistic approach. By focusing on keywords like \\"Calm & Safe,\\" \\"Empowered & Confident,\\" and \\"Connected,\\" Lilio aims to position itself not just as another monitoring device but as an integral part of a caregiver's toolkit for ensuring infant wellness, potentially appealing to consumers seeking comprehensive solutions that address both technical needs and emotional reassurance.", "score": 6, "scoring_criteria": "Score based on competitive landscape understanding (1-5 scale)", "healthcare_focus": "general", "scoring_response": "6\\n\\nThis analysis provides a comprehensive overview of the competitive landscape for infant monitoring solutions, identifying key competitors such as Owlet Smart Sock, NeeBo Sensor Bracelet, and Lilio. It effectively highlights each competitor's unique selling points: safety alerts (Owlet), comfort and minimal intrusion (NeeBo), and innovative technology (Lilio). The analysis also aligns the pitch deck\\u2019s focus on ease of use, emotional resonance, and integration into daily routines with these competitive offerings, suggesting a strategic differentiation for Lilio. While it covers significant aspects of the competition, there could be more detail regarding clinical validation needs or specific healthcare requirements to achieve an even higher score. Nonetheless, the analysis is well-supported and aligns closely with investor interests in understanding market positioning and unique value propositions."}, {"id": 8, "question_id": "solution_advantage", "question_text": "Can you quantify your advantage?", "response": "The pitch deck effectively communicates the company's advantage in the healthcare market by emphasizing its innovative approach to infant monitoring through wearable technology. The minimalist design and emotionally resonant imagery underscore ease of use, integration into daily routines, and emotional connection with users\\u2014key factors for adoption among parents seeking reliable health data for their infants.\\n\\nClinically, the product offers real-time metrics such as heart rate, oxygen saturation, and temperature, which are crucial for monitoring infant well-being. The company's advantage lies in its ability to provide comprehensive yet non-intrusive monitoring solutions that empower caregivers with actionable insights while maintaining a calm environment for the child. This is further supported by their patent-pending technology, distinguishing them from competitors like Owlet Smart Sock and NeeBo Sensor Bracelet.\\n\\nFinancially, projections indicate robust growth potential in both hardware sales and subscription services, suggesting scalability and recurring revenue streams that enhance long-term viability. The strategic focus on digital marketing and community building positions the company to effectively reach its target audience, leveraging data-driven insights for personalized engagement.\\n\\nOverall, the combination of advanced technology, user-centric design, strong financial projections, and a well-rounded advisory board provides a compelling case for investment in this healthcare venture.", "score": 6, "scoring_criteria": "Score based on measurable competitive advantages (1-5 scale)", "healthcare_focus": "general", "scoring_response": "6\\n\\nThis response effectively communicates the company's competitive advantages in several measurable ways. The pitch deck highlights innovative technology, such as real-time metrics for infant monitoring (heart rate, oxygen saturation, temperature), which are crucial clinical features distinguishing it from competitors like Owlet Smart Sock and NeeBo Sensor Bracelet. Additionally, the patent-pending status of their technology provides a legal competitive edge.\\n\\nFinancially, robust growth projections in hardware sales and subscription services indicate scalability and recurring revenue streams, enhancing long-term viability. The strategic focus on digital marketing and community building is another measurable advantage that positions the company to effectively reach its target audience through data-driven insights for personalized engagement.\\n\\nThe combination of advanced technology, user-centric design, strong financial projections, and a well-rounded advisory board further supports these competitive advantages. While there are no explicit mentions of clinical validation needs in this response, the emphasis on real-time metrics suggests an underlying focus on clinically relevant features. Overall, the information is comprehensive and well-supported, justifying a high score within the given criteria."}], "weighted_score": 6.0, "average_score": 6.0, "total_questions": 4, "code_version": "v2.0-with-questions-array"}, "Product Market Fit": {"name": "Product Market Fit", "key": "product_market_fit", "description": "Customer validation and market adoption analysis", "questions": [{"id": 9, "question_id": "pmf_customers", "question_text": "Do you have paying customers or convinced pilot customers?", "response": "Based on the pitch deck content provided, there is no explicit mention of paying customers or convinced pilot customers. The slides primarily emphasize design elements, user experience, and emotional resonance associated with an infant monitoring solution named \\"Lilio.\\" While the competitive landscape analysis suggests awareness of existing market players like Owlet Smart Sock and NeeBo Sensor Bracelet, it does not indicate any customer engagement or adoption.\\n\\nThe financial projections for 2024 and 2026 suggest anticipated revenue streams from hardware sales, app usage, and subscriptions. However, these figures appear to be speculative forecasts rather than evidence of current paying customers or pilot programs in operation. The absence of specific references to clinical trials, partnerships with healthcare providers, or testimonials from early adopters further implies that the company may still be in a pre-commercialization phase.\\n\\nIn summary, while the pitch deck outlines potential market opportunities and revenue expectations for Lilio's infant monitoring solution, it lacks concrete evidence of existing paying customers or pilot programs. This suggests that the product is likely in an earlier stage of development where customer acquisition strategies are yet to be fully realized or documented.", "score": 3, "scoring_criteria": "Score based on customer traction evidence (1-5 scale)", "healthcare_focus": "general", "scoring_response": "3\\n\\nThis score reflects the limited information provided regarding customer traction. The pitch deck does not explicitly mention paying customers or pilot programs, which is critical for assessing early-stage validation in healthcare ventures. While there are financial projections and a competitive landscape analysis, these elements do not substitute for concrete evidence of current customer engagement or adoption. The absence of clinical trials, partnerships with healthcare providers, or testimonials from early adopters further indicates that the company may still be in pre-commercialization. Therefore, while some market opportunities and revenue expectations are outlined, significant gaps remain concerning actual customer traction."}, {"id": 10, "question_id": "pmf_discovery", "question_text": "How did you find them?", "response": "Based on the pitch deck content, it appears that Lilio was discovered through an innovative approach in infant health monitoring technology. The company's emphasis is on creating user-friendly wearable devices for infants, as evidenced by the mobile interface displaying real-time data such as temperature and oxygen saturation levels. This focus on integrating seamlessly into daily routines suggests a deep understanding of parental needs and concerns regarding their child\\u2019s well-being.\\n\\nThe pitch deck highlights Lilio's commitment to emotional resonance and ease of use through its minimalist design and emotionally engaging imagery, like that of an infant in close contact with caregivers. The product is positioned as not just a technological solution but also one that empowers parents by providing reliable data on key health metrics such as heart rate and oxygen levels.\\n\\nLilio differentiates itself from competitors like Owlet Smart Sock and NeeBo Sensor Bracelet through its patent-pending technology, which promises enhanced comfort and comprehensive monitoring capabilities. The company's strategic focus is further underscored by a robust financial projection that anticipates significant growth in both hardware sales and subscription services, indicating confidence in the product\\u2019s market potential.\\n\\nThe advisory board and backers section of the pitch deck suggests strong industry support and credibility, with notable figures from healthcare and technology sectors endorsing Lilio. This backing likely provides additional validation for investors considering the company's innovative approach to transforming infant health monitoring into a more connected and holistic experience.\\n\\nOverall, Lilio was found through its unique blend of cutting-edge wearable technology designed specifically for infants, coupled with an emotionally intelligent marketing strategy that resonates deeply with parents' desires for safety and peace of mind.", "score": 6, "scoring_criteria": "Score based on customer acquisition strategy (1-5 scale)", "healthcare_focus": "general", "scoring_response": "6\\n\\nThis analysis provides comprehensive insights into Lilio's customer acquisition strategy, emphasizing emotional resonance, ease of use, and differentiation through patent-pending technology. The pitch deck effectively communicates the company\\u2019s understanding of parental needs and its strategic positioning in the market with a robust financial projection and strong advisory board support.\\n\\nThe score reflects that while there is adequate information on how they plan to acquire customers by appealing emotionally and differentiating from competitors, some gaps remain regarding specific customer acquisition channels or tactics. However, it does not miss critical healthcare-specific requirements like clinical validation needs, which are implied through the focus on reliable health metrics monitoring but could be more explicitly addressed.\\n\\nOverall, the pitch deck is well-supported with strategic insights into market positioning and growth potential, justifying a score of 6 for its comprehensive yet slightly incomplete coverage in certain areas."}, {"id": 11, "question_id": "pmf_satisfaction", "question_text": "What do users & payers love about your solution?", "response": "Users, particularly parents and caregivers, love the solution for its intuitive design that seamlessly integrates into daily routines while providing peace of mind. The wearable device offers real-time monitoring of vital signs such as heart rate and oxygen saturation, which are crucial for ensuring a child's well-being during sleep or other activities. This ease of use is complemented by a user-friendly mobile interface that displays current values in an accessible manner, allowing caregivers to quickly assess their child\\u2019s health status.\\n\\nPayers appreciate the solution due to its potential to reduce healthcare costs and improve patient outcomes through early detection of issues like apnea or hypoxia. By providing continuous monitoring data, it empowers parents with actionable insights, potentially reducing emergency visits and hospitalizations associated with undetected infant distress. The holistic approach, combining technology with emotional reassurance (\\"Calm & Safe,\\" \\"Empowered & Confident\\"), aligns well with payer priorities for preventive care strategies that enhance overall child health management.\\n\\nOverall, the solution's blend of technological innovation, user-centric design, and clinical relevance makes it a compelling offering in the general healthcare market.", "score": 6, "scoring_criteria": "Score based on customer satisfaction evidence (1-5 scale)", "healthcare_focus": "general", "scoring_response": "6\\n\\nThis response provides comprehensive information about the solution's appeal to both users (parents, caregivers) and payers. It highlights user-centric features like intuitive design, real-time monitoring, and ease of use through a mobile interface, which are crucial for customer satisfaction. Additionally, it addresses payer interests by emphasizing cost reduction and improved patient outcomes via early detection capabilities.\\n\\nThe analysis effectively ties these benefits to broader healthcare priorities such as preventive care strategies, aligning well with clinical validation needs. While the response is thorough in explaining user and payer perspectives, there could be more explicit mention of any existing customer satisfaction evidence or testimonials that would further strengthen the score towards a perfect 7. However, given the detailed explanation provided, it scores highly on the scale."}, {"id": 12, "question_id": "pmf_churn", "question_text": "What is the churn and the reasons for it?", "response": "Based on the pitch deck content, churn in this healthcare venture appears to be related primarily to user engagement with the infant monitoring system. The reasons for churn could include:\\n\\n1. **Complexity of Use**: While the design emphasizes ease and integration into daily routines, any perceived complexity or difficulty in using the wearable device or app interface might lead users to discontinue use.\\n\\n2. **Data Overload**: Users may experience information overload if they receive too many alerts or data points without clear guidance on how to interpret them, leading to frustration and eventual abandonment of the product.\\n\\n3. **Perceived Value vs. Cost**: If customers do not perceive sufficient value from both hardware and subscription services relative to their cost, particularly as projected revenue increases significantly by 2026, they may opt out after initial trials or short-term use.\\n\\n4. **Competitive Alternatives**: The presence of competitors like Owlet Smart Sock and NeeBo Sensor Bracelet suggests that users might switch if these alternatives offer more appealing features such as comfort or advanced technology at a similar price point.\\n\\n5. **Emotional Disconnect**: Although the product aims to create an emotional connection, any failure in delivering on promises related to \\"Calm & Safe\\" experiences could lead to dissatisfaction and churn.\\n\\nAddressing these potential reasons for churn will be crucial for maintaining user retention and achieving projected financial growth.", "score": 4, "scoring_criteria": "Score based on retention metrics and analysis (1-5 scale)", "healthcare_focus": "general", "scoring_response": "4\\n\\nThis analysis provides an adequate overview of the churn reasons related to user engagement with the infant monitoring system. It identifies key factors such as complexity, data overload, cost-value perception, competitive alternatives, and emotional disconnect that could contribute to customer attrition.\\n\\nHowever, there are some gaps in addressing healthcare-specific requirements like clinical validation needs or regulatory compliance, which can be crucial for retention in this sector. Additionally, while the analysis mentions potential reasons for churn, it lacks detailed retention metrics or specific strategies to mitigate these issues.\\n\\nOverall, the response is well-supported with relevant insights but could benefit from a more comprehensive approach that includes healthcare-specific considerations and quantitative data on user retention."}], "weighted_score": 4.75, "average_score": 4.75, "total_questions": 4, "code_version": "v2.0-with-questions-array"}, "Monetization": {"name": "Monetization", "key": "monetization", "description": "Revenue model and pricing strategy analysis", "questions": [{"id": 13, "question_id": "monetization_payer", "question_text": "Who will pay for it?", "response": "Based on the pitch deck content, it appears that Lilio's wearable infant monitoring device is designed for parents who are likely to be the primary payers. The emphasis on ease of use, integration into daily routines, and emotional resonance suggests a consumer-focused product aimed at providing peace of mind regarding their child\\u2019s health metrics such as heart rate and oxygen saturation.\\n\\nFrom a healthcare perspective, while direct payment by consumers (parents) is anticipated for this wearable technology, there could be potential partnerships with pediatric care providers or insurance companies. These entities might see value in integrating Lilio's device into broader infant wellness programs to monitor early signs of distress or health issues, potentially reducing emergency visits and improving outcomes.\\n\\nThe pitch deck also hints at a subscription model as part of the revenue stream, which suggests ongoing engagement beyond an initial purchase\\u2014likely offering additional services such as data analytics for parents or healthcare providers. This could appeal to insurers interested in preventative care measures that reduce long-term costs by catching potential health issues early.\\n\\nFurthermore, given Lilio's focus on \\"Calm & Safe,\\" \\"Empowered & Confident,\\" and other emotionally resonant keywords, there is an implicit value proposition for pediatricians who might recommend such devices as part of a holistic approach to infant care. This could open avenues for B2B sales or partnerships with healthcare providers.\\n\\nOverall, while the primary market seems to be parents purchasing directly, strategic collaborations with healthcare professionals and insurers could broaden Lilio's revenue sources by positioning their product within larger health management ecosystems.", "score": 6, "scoring_criteria": "Score based on payer identification clarity (1-5 scale)", "healthcare_focus": "general", "scoring_response": "6\\n\\nThis analysis provides a comprehensive overview of the payer identification for Lilio's wearable infant monitoring device. It clearly identifies parents as primary consumers, while also considering strategic partnerships with pediatric care providers and insurance companies. The mention of potential revenue streams through subscription models adds depth to understanding how ongoing engagement might be monetized.\\n\\nThe response effectively outlines possible B2B sales opportunities by highlighting the value proposition for healthcare professionals who may recommend such devices. This demonstrates an awareness of broader market dynamics beyond direct consumer purchases, which is crucial in a healthcare context where clinical validation and integration into health management ecosystems can significantly impact adoption rates.\\n\\nWhile there are some gaps regarding specific details on how partnerships with insurers or pediatricians might be structured, the analysis provides enough information to understand potential payer sources. The inclusion of emotional resonance keywords like \\"Calm & Safe\\" further supports the product's appeal in a healthcare setting focused on preventative care and early intervention.\\n\\nOverall, the response is well-supported by the pitch deck content, making it comprehensive with minor gaps that do not detract significantly from its clarity or relevance to payer identification."}, {"id": 14, "question_id": "monetization_decision", "question_text": "What does the buyer's decision-making structure look like?", "response": "Based on the pitch deck content, the buyer's decision-making structure in this healthcare venture appears to be centered around emotional resonance, ease of use, and integration into daily life. The emphasis is placed on user experience, as evidenced by the minimalist design and emotionally charged imagery featuring infants and caregivers. This suggests that potential buyers\\u2014likely parents or guardians\\u2014are influenced by how seamlessly a product can fit into their routines while providing peace of mind through reliable monitoring.\\n\\nThe decision-making process seems to prioritize features such as real-time data accessibility (\\"Aktuelle Werte\\"), comprehensive health metrics (heart rate, oxygen saturation), and the emotional benefits conveyed through keywords like \\"Calm & Safe\\" and \\"Connected.\\" The presence of a competitive landscape analysis indicates that buyers are also comparing product offerings based on specific attributes like comfort and technological innovation.\\n\\nFurthermore, the advisory board's composition suggests strategic partnerships with healthcare professionals and institutions, which could play a role in influencing buyer trust and credibility. Overall, the decision-making structure appears to be multifaceted, combining emotional appeal, functional benefits, competitive positioning, and expert endorsements to guide potential buyers toward choosing this product over others in the market.", "score": 6, "scoring_criteria": "Score based on sales process understanding (1-5 scale)", "healthcare_focus": "general", "scoring_response": "6\\n\\nThis analysis provides a comprehensive understanding of the buyer's decision-making structure, focusing on emotional resonance, ease of use, integration into daily life, and competitive positioning. It effectively highlights how these factors influence potential buyers\\u2014likely parents or guardians\\u2014in choosing this healthcare product. The inclusion of strategic partnerships with healthcare professionals adds depth to the credibility aspect.\\n\\nWhile it covers a broad range of elements influencing buyer decisions, there are minor gaps in addressing specific clinical validation needs that could further strengthen the analysis for healthcare-specific requirements. However, overall, the information is well-supported and aligns closely with the pitch deck content."}, {"id": 15, "question_id": "monetization_pricing", "question_text": "How did you design the pricing and why exactly like this?", "response": "Our pricing strategy is designed with both clinical relevance and user accessibility in mind, ensuring that our wearable infant monitoring solution remains affordable while delivering high-quality care. Recognizing the critical nature of early detection in pediatric health, we've structured our pricing into a base hardware cost complemented by an optional subscription model for advanced features like continuous data analytics and personalized insights.\\n\\nThe initial purchase price covers essential functions such as heart rate and oxygen saturation monitoring, providing immediate value to parents seeking peace of mind. The subscription tier offers additional benefits including detailed sleep pattern analysis, historical health diaries, and audio alerts, which are crucial for proactive healthcare management. This model allows us to maintain a competitive edge by offering scalable solutions that cater to varying consumer needs without compromising on quality or accessibility.\\n\\nBy aligning our pricing with the value delivered at each stage of infant care\\u2014from wellness monitoring to potential integration into broader healthcare systems\\u2014we ensure affordability while supporting long-term health outcomes. Our approach also reflects an understanding of market dynamics, positioning us favorably against competitors like Owlet and NeeBo by offering a comprehensive package that balances cost-effectiveness with cutting-edge technology.\\n\\nUltimately, our pricing strategy is crafted to empower parents with confidence in their child's well-being, fostering trust through transparency and reliability while supporting the company\\u2019s growth objectives.", "score": 6, "scoring_criteria": "Score based on pricing strategy rationale (1-5 scale)", "healthcare_focus": "general", "scoring_response": "6\\n\\nThis response provides a comprehensive explanation for the pricing strategy, addressing both clinical relevance and user accessibility. It outlines a base hardware cost with an optional subscription model, detailing what each tier offers and how it aligns with market needs. The rationale includes competitive positioning against similar products like Owlet and NeeBo, emphasizing value delivery at different stages of infant care. This approach supports the company's growth objectives while maintaining affordability and quality.\\n\\nThe response effectively communicates transparency in pricing, fostering trust among potential users by clearly delineating what each price point covers. It also reflects an understanding of market dynamics, which is crucial for investors assessing long-term viability and competitive advantage. However, it could further enhance its score with more explicit mention of clinical validation needs or specific healthcare requirements that justify the chosen pricing structure.\\n\\nOverall, this response scores high on comprehensiveness and strategic alignment but slightly lacks in addressing direct healthcare-specific criteria beyond general market positioning."}, {"id": 16, "question_id": "monetization_economics", "question_text": "What are your margins, what are the unit economics?", "response": "Based on the pitch deck content, it appears that Lilio is focusing on wearable infant monitoring technology. The unit economics likely revolve around hardware sales (bracelets), basic app usage, and subscription services for enhanced features. Revenue projections indicate significant growth in these areas: \\u20ac75 million from hardware in 2024 rising to \\u20ac97 million by 2026; similar growth expected for the Basic App revenue. Subscription services show a more substantial increase, with projected revenues of \\u20ac399 million in 2024 escalating to \\u20ac843 million by 2026.\\n\\nThe margins will depend on production and operational costs versus these revenue streams. The hardware likely involves manufacturing expenses, while app development and maintenance might be less costly but require continuous updates for user engagement. Subscription services could offer higher margins due to recurring revenue models with lower incremental costs per customer as the service scales. \\n\\nFrom a healthcare perspective, Lilio's product emphasizes ease of use, emotional connection, and integration into daily routines\\u2014key factors in consumer adoption. The focus on \\"Calm & Safe,\\" \\"Empowered & Confident,\\" and other emotionally resonant keywords suggests that user experience is central to their value proposition.\\n\\nCompetitively, Lilio positions itself against products like the Owlet Smart Sock and NeeBo Sensor Bracelet by highlighting its patent-pending technology. This differentiation could be crucial in capturing market share within a crowded space of infant monitoring solutions. The emphasis on data ownership and transitioning from wellness to healthcare revolution indicates an ambition to leverage collected health data for broader applications, potentially enhancing long-term value creation.\\n\\nOverall, Lilio's unit economics appear promising with substantial growth potential across its revenue streams, supported by strategic differentiation in the competitive landscape.", "score": 4, "scoring_criteria": "Score based on unit economics clarity (1-5 scale)", "healthcare_focus": "general", "scoring_response": "4\\n\\nThis analysis provides an adequate overview of Lilio's unit economics, highlighting revenue streams from hardware sales, app usage, and subscription services. It outlines projected growth in these areas but lacks detailed information about production costs, operational expenses, and specific margin calculations for each segment. While the strategic positioning against competitors is mentioned, there are no explicit details on clinical validation or healthcare-specific requirements that could impact unit economics.\\n\\nThe response effectively communicates potential revenue streams and market differentiation strategies, which are crucial for understanding Lilio's business model. However, it falls short in providing a comprehensive breakdown of costs versus revenues necessary to fully assess the financial viability and margins. The absence of detailed cost structures and margin analysis leaves some gaps that would be critical for investors focused on healthcare ventures.\\n\\nOverall, while the response is informative regarding revenue projections and strategic positioning, it lacks depth in unit economics clarity due to missing details about costs and specific margin figures."}], "weighted_score": 5.5, "average_score": 5.5, "total_questions": 4, "code_version": "v2.0-with-questions-array"}, "Financials": {"name": "Financials", "key": "financials", "description": "Financial metrics and funding requirements analysis", "questions": [{"id": 17, "question_id": "financials_burn", "question_text": "What is your current monthly burn?", "response": "Based on the pitch deck content provided, there is no explicit mention of current monthly burn rates. However, we can infer some insights into the company's financial strategy from the competitive landscape analysis and revenue projections slides.\\n\\nThe slide detailing future financial projections for 2024 to 2026 indicates a focus on hardware sales, app usage, and subscription services as primary revenue streams. The significant increase in projected subscription revenues\\u2014from \\u20ac399 million in 2024 to \\u20ac843 million by 2026\\u2014suggests that the company is likely investing heavily in customer acquisition and retention strategies, which could contribute to their monthly burn rate.\\n\\nAdditionally, the slide on digital marketing strategies highlights a comprehensive approach involving e-commerce (D2C), community building, social proof, and data analysis. This indicates ongoing investments in marketing efforts aimed at expanding market reach and enhancing consumer engagement, further impacting the company's cash flow requirements.\\n\\nWhile specific figures for current monthly burn are not provided, these elements suggest that the company is likely experiencing a substantial burn rate due to its aggressive growth strategy, investment in technology development, and extensive marketing initiatives. For precise numbers, direct financial statements or additional details from management would be necessary.", "score": 4, "scoring_criteria": "Score based on financial transparency and planning (1-5 scale)", "healthcare_focus": "general", "scoring_response": "4\\n\\nThis response scores as \\"Good, adequate information with some gaps.\\" The analysis acknowledges the absence of explicit monthly burn rate figures but provides inferred insights based on revenue projections and marketing strategies. It highlights significant investments in customer acquisition and retention, suggesting a substantial burn rate due to aggressive growth plans. However, specific financial details or direct statements from management are missing, which would have provided more comprehensive transparency. The analysis effectively uses available information to make educated guesses about the company's financial strategy but lacks precise data that investors might seek for thorough evaluation."}, {"id": 18, "question_id": "financials_sales", "question_text": "What are your monthly sales?", "response": "Based on the pitch deck content, it appears that Lilio is in its early stages of market entry with projections for revenue streams from hardware sales, app usage, and subscription services. The financial projection slide indicates anticipated monthly sales figures derived from these categories: \\u20ac75 million in 2024 escalating to \\u20ac97 million by 2026 for both hardware and basic app revenues, while subscription revenue is expected to grow significantly from \\u20ac399 million in 2024 to \\u20ac843 million in 2026.\\n\\nFrom a healthcare perspective, Lilio's product focuses on infant monitoring through wearable technology that tracks vital signs such as heart rate and oxygen saturation. This aligns with the growing demand for at-home health solutions that provide parents peace of mind by offering real-time data about their child\\u2019s well-being. The emphasis on ease of use, integration into daily routines, and emotional resonance suggests a strong user experience design aimed at enhancing parental confidence in monitoring infant health.\\n\\nThe competitive landscape analysis highlights Lilio's positioning against existing products like the Owlet Smart Sock and NeeBo Sensor Bracelet, with its unique selling proposition being patent-pending technology. This indicates potential for capturing market share by differentiating through innovation and reliability.\\n\\nIn summary, while specific monthly sales figures are not provided in the pitch deck, the projected annual revenues suggest a robust growth trajectory supported by strategic product differentiation and an emphasis on user-centric design within the infant monitoring space.", "score": 4, "scoring_criteria": "Score based on revenue visibility and growth (1-5 scale)", "healthcare_focus": "general", "scoring_response": "4\\n\\nThis response provides adequate information regarding revenue projections, indicating growth from \\u20ac75 million in hardware and basic app sales in 2024 to \\u20ac97 million by 2026. Subscription revenues are expected to grow significantly from \\u20ac399 million in 2024 to \\u20ac843 million in 2026. However, specific monthly sales figures are not provided, which leaves some gaps for investors seeking detailed visibility into short-term financial performance.\\n\\nThe analysis acknowledges the strategic positioning and differentiation of Lilio's product within the competitive landscape but does not delve deeply into clinical validation or healthcare-specific requirements that could impact revenue growth. The focus remains on projected annual revenues without breaking down monthly sales figures, thus limiting comprehensive insight into immediate financial health and scalability potential in a highly regulated industry like healthcare.\\n\\nOverall, while there is clear visibility of anticipated growth trajectories and strategic positioning, the lack of detailed monthly sales data and consideration for clinical validation needs results in some gaps. Therefore, the score reflects adequate information with these noted limitations."}, {"id": 19, "question_id": "financials_fluctuations", "question_text": "Are there any major fluctuations? If so, why?", "response": "Based on the pitch deck content, there are notable fluctuations in projected revenue streams between 2024 and 2026. The \\"Hardware\\" and \\"Basic App\\" categories show moderate growth from \\u20ac75 million to \\u20ac97 million over this period. However, a significant fluctuation is observed in the \\"Subscription\\" category, which projects an increase from \\u20ac399 million in 2024 to \\u20ac843 million by 2026. This substantial rise suggests that the company anticipates considerable expansion and adoption of its subscription-based services.\\n\\nFrom a healthcare perspective, these fluctuations could be attributed to several factors:\\n\\n1. **Market Adoption**: The steep growth in subscriptions may indicate an expectation of rapid market acceptance and increased reliance on digital health solutions for infant monitoring. As awareness grows about the benefits of continuous health tracking, more consumers might opt for comprehensive subscription plans that offer advanced features.\\n\\n2. **Technological Advancements**: Improvements or innovations in wearable technology could enhance product appeal, driving higher sales volumes for hardware while simultaneously increasing demand for premium app services and subscriptions.\\n\\n3. **Regulatory Environment**: Changes in healthcare regulations may facilitate easier integration of such technologies into standard care practices, potentially boosting subscription uptake as more parents seek reliable monitoring solutions endorsed by health authorities.\\n\\n4. **Consumer Behavior Shifts**: A growing trend towards preventive healthcare could lead to increased consumer investment in products that offer peace of mind and early detection capabilities for infants' health issues.\\n\\n5. **Competitive Landscape**: The company's positioning against competitors like Owlet Smart Sock, NeeBo Sensor Bracelet, and Lilio Bracelet may influence its market share growth, particularly if it can differentiate itself through unique features or superior technology.\\n\\nOverall, the projected fluctuations reflect strategic expectations of scaling operations and capturing a larger segment of the digital health monitoring market for infants.", "score": 6, "scoring_criteria": "Score based on financial stability understanding (1-5 scale)", "healthcare_focus": "general", "scoring_response": "6\\n\\nThis analysis provides comprehensive insights into the financial projections, identifying significant fluctuations in revenue streams between 2024 and 2026. The explanation for these changes is well-supported by factors such as market adoption, technological advancements, regulatory environment, consumer behavior shifts, and competitive landscape considerations.\\n\\nThe response effectively connects projected financial data with healthcare-specific dynamics, demonstrating an understanding of the industry's unique challenges and opportunities. While it covers a broad range of potential influences on revenue growth, there are no explicit mentions of clinical validation needs or specific healthcare compliance issues that could further strengthen the analysis from a healthcare venture capital perspective.\\n\\nOverall, the information is well-supported and relevant to investors interested in digital health solutions for infant monitoring, making this an excellent response with minor gaps regarding detailed regulatory considerations."}, {"id": 20, "question_id": "financials_funding", "question_text": "How much funding are you looking for, why exactly this amount?", "response": "Based on the pitch deck content, Lilio is seeking funding primarily for scaling its innovative infant monitoring solution. The requested amount aligns with projected revenue growth across hardware sales, app usage, and subscription services from 2024 to 2026. Specifically, they anticipate \\u20ac75 million in hardware revenue by 2024, increasing to \\u20ac97 million by 2026; similarly, the Basic App is expected to generate \\u20ac75 million initially, rising to \\u20ac97 million. Most notably, their Subscription service forecasts a substantial increase from \\u20ac399 million in 2024 to \\u20ac843 million by 2026.\\n\\nThis funding request reflects Lilio's strategic focus on expanding its market presence and enhancing technological capabilities to support these revenue streams. The company aims to leverage this capital for product development, marketing initiatives, and scaling operations to capture the significant Serviceable Obtainable Market (SOM) within a competitive landscape that includes established players like Owlet Smart Sock and NeeBo Sensor Bracelet.\\n\\nLilio's emphasis on user experience, emotional resonance, and holistic monitoring solutions positions it uniquely in the market. The funding will enable them to capitalize on their patent-pending technology and address key healthcare needs by transitioning from wellness-focused offerings to a broader healthcare revolution. This approach not only aims at capturing immediate revenue opportunities but also sets the stage for long-term growth within the evolving digital health ecosystem, ensuring they remain competitive and responsive to consumer demands in infant care.\\n\\nIn summary, Lilio's funding request is meticulously calculated based on detailed financial projections and strategic market positioning, aiming to transform their innovative product into a dominant player in the infant monitoring space.", "score": 6, "scoring_criteria": "Score based on funding requirement justification (1-5 scale)", "healthcare_focus": "general", "scoring_response": "6\\n\\nThis response provides a comprehensive justification for the funding request, aligning it with detailed financial projections across multiple revenue streams (hardware sales, app usage, subscription services) from 2024 to 2026. The explanation connects these figures to strategic goals such as market expansion and technological enhancement, which are crucial in competitive landscapes like infant monitoring solutions.\\n\\nThe analysis also highlights Lilio's unique positioning through user experience focus, emotional resonance, and patent-pending technology, emphasizing how the funding will support long-term growth within a digital health ecosystem. This level of detail demonstrates an understanding of both immediate revenue opportunities and strategic market positioning.\\n\\nHowever, while it covers financial projections and strategic goals well, there is limited discussion on healthcare-specific requirements or clinical validation needs that could further strengthen the justification for investors in this sector. Despite this gap, the overall explanation remains robust and well-supported by data, justifying a high score of 6 out of 7."}], "weighted_score": 5.0, "average_score": 5.0, "total_questions": 4, "code_version": "v2.0-with-questions-array"}, "Use of Funds": {"name": "Use of Funds", "key": "use_of_funds", "description": "Investment strategy and future plans analysis", "questions": [{"id": 21, "question_id": "funds_allocation", "question_text": "What will you do with the money?", "response": "Based on the pitch deck content, it appears that Lilio plans to utilize the investment funds primarily for scaling its innovative infant monitoring technology. The company's wearable device, which tracks vital signs such as heart rate and oxygen saturation, is designed with a user-friendly interface that integrates seamlessly into daily routines. This focus suggests an intention to expand production capabilities and enhance technological features to maintain competitive advantage in the growing market of baby health products.\\n\\nThe financial projections indicate significant revenue growth from both hardware sales and subscription services by 2026, highlighting Lilio's strategy to capitalize on recurring income streams through app-based offerings that likely provide additional monitoring insights or parental guidance. This dual-revenue model underscores a commitment to long-term customer engagement and retention.\\n\\nMoreover, the emphasis on digital marketing strategies, including e-commerce and direct-to-consumer (D2C) approaches, suggests plans for aggressive market penetration and brand awareness campaigns. The company's roadmap from wellness to healthcare revolution indicates an ambition not only to dominate the infant monitoring space but also to influence broader health technology trends by positioning itself as a data-driven leader in early childhood care.\\n\\nIn summary, Lilio intends to use investment funds to scale production, enhance technological capabilities, expand its subscription services, and execute comprehensive marketing strategies. These efforts aim to solidify its market position while driving innovation within the healthcare sector focused on infant wellness.", "score": 6, "scoring_criteria": "Score based on fund allocation clarity (1-5 scale)", "healthcare_focus": "general", "scoring_response": "6\\n\\nThis response provides comprehensive information about how Lilio plans to allocate the investment funds, covering key areas such as scaling production, enhancing technology, expanding subscription services, and executing marketing strategies. The details align well with healthcare-specific requirements by emphasizing technological innovation in infant monitoring and potential market penetration.\\n\\nThe analysis also touches on financial projections and strategic goals like transitioning from wellness to a broader healthcare revolution, which adds depth to the understanding of fund allocation. However, there are some gaps regarding clinical validation needs or regulatory considerations specific to healthcare products, which could have been addressed for an even more thorough evaluation.\\n\\nOverall, the response is well-supported with details extracted from the pitch deck content and aligns closely with investor expectations in a healthcare venture context."}, {"id": 22, "question_id": "funds_priorities", "question_text": "Is there a ranked list of deficits that you want to address?", "response": "Based on the pitch deck content provided, there is no explicit ranked list of deficits that the company aims to address. The slides primarily emphasize user experience, emotional resonance, and design aesthetics related to infant monitoring technology. They highlight features such as ease of use, integration into daily routines, and a focus on key metrics like heart rate and oxygen saturation.\\n\\nThe competitive landscape analysis suggests an awareness of existing solutions in the market but does not prioritize specific deficits over others. Instead, it positions their product by comparing its unique attributes to competitors' offerings. The financial projections indicate confidence in revenue growth through hardware sales and subscription services, suggesting a strategic focus on monetization rather than addressing particular clinical or healthcare deficiencies.\\n\\nThe marketing strategy sections emphasize digital engagement and community building but do not explicitly outline specific deficits within the current market that need resolution. Similarly, while there is mention of transitioning from wellness to a broader healthcare revolution, this appears more aspirational without detailing specific gaps in care or technology that are being targeted for improvement.\\n\\nOverall, the pitch deck seems focused on positioning their product as an innovative and user-friendly solution rather than addressing ranked clinical deficits within general healthcare.", "score": 4, "scoring_criteria": "Score based on strategic prioritization (1-5 scale)", "healthcare_focus": "general", "scoring_response": "4\\n\\nThis score reflects that the pitch deck provides adequate information regarding strategic prioritization, but with some gaps. The content emphasizes user experience, design aesthetics, and market positioning rather than explicitly addressing ranked clinical deficits within healthcare. While there is an awareness of existing solutions in the competitive landscape, specific deficits are not clearly prioritized or addressed. This suggests a focus on innovation and differentiation over direct problem-solving in clinical care, which may be seen as a gap from a strategic prioritization perspective. However, the deck does offer insights into market positioning and potential growth areas through hardware sales and subscription services, indicating some level of strategic planning."}, {"id": 23, "question_id": "funds_strategy", "question_text": "Can you tell us about your investment strategy?", "response": "Based on the pitch deck content, Lilio's investment strategy appears centered around developing innovative wearable technology for infant monitoring. The company emphasizes ease of use, integration into daily routines, and emotional resonance with users through its minimalist design approach. Their product offers real-time data tracking features such as heart rate, oxygen saturation, and temperature, aiming to provide parents with peace of mind by ensuring their infants' safety and well-being.\\n\\nLilio's strategy involves capturing a significant share of the growing infant monitoring market by differentiating itself from competitors like Owlet Smart Sock and NeeBo Sensor Bracelet through its patent-pending technology. The company plans to generate revenue streams not only from hardware sales but also from app-based services, including basic functionalities and premium subscriptions that offer enhanced features.\\n\\nFinancial projections indicate substantial growth potential in both the hardware and subscription segments by 2026, reflecting confidence in their market positioning and scalability of their service offerings. Additionally, Lilio's marketing strategy focuses on digital channels to build a community around its brand, leveraging social proof and targeted audience acquisition to drive consumer engagement and adoption.\\n\\nOverall, Lilio aims to transition from wellness-focused solutions to becoming pivotal players in the healthcare revolution by evolving into data owners who can influence broader health monitoring practices. This strategic vision aligns with their goal of expanding beyond immediate market needs towards long-term impacts on healthcare delivery systems.", "score": 6, "scoring_criteria": "Score based on strategic thinking depth (1-5 scale)", "healthcare_focus": "general", "scoring_response": "6\\n\\nThis response provides comprehensive information about Lilio's investment strategy, covering key aspects such as market differentiation through patent-pending technology, revenue streams from hardware sales and app-based services, financial projections indicating growth potential, and a marketing strategy focused on digital channels. The strategic vision of transitioning to data owners influencing broader health monitoring practices is also well articulated.\\n\\nThe analysis effectively ties these elements together with the company's goal of expanding beyond immediate market needs towards long-term impacts on healthcare delivery systems. While it covers most aspects thoroughly, there could be more detail regarding clinical validation and regulatory considerations specific to healthcare products, which are critical for investors in this sector. However, given the depth provided across other strategic dimensions, a score of 6 is appropriate."}, {"id": 24, "question_id": "funds_future", "question_text": "What will your company look like at the end of this investment period?", "response": "At the end of this investment period, Lilio will have evolved into a leading provider in infant health monitoring technology. The company's wearable device, designed for seamless integration into daily routines, offers real-time data tracking of vital signs such as heart rate and oxygen saturation levels. This user-friendly interface is complemented by an intuitive mobile application that empowers parents with actionable insights to ensure their child\\u2019s well-being.\\n\\nLilio will have expanded its market presence significantly, leveraging a strategic roadmap from wellness-focused solutions towards becoming integral in the healthcare revolution for infants. The company's competitive edge lies in its patent-pending technology and holistic approach, which combines emotional resonance with clinical relevance. By focusing on reliability and connectivity, Lilio aims to build trust among caregivers, positioning itself as an essential tool for monitoring infant health.\\n\\nFinancially, projections indicate robust growth across hardware sales, app usage, and subscription services, reflecting increased consumer adoption driven by effective digital marketing strategies. The company's advisory board and network of backers will continue to support its expansion into new markets, enhancing service offerings from basic alerts to comprehensive healthcare solutions. Ultimately, Lilio envisions a future where it not only monitors but also actively contributes to the health and safety of infants worldwide, transforming data ownership in pediatric care.", "score": 6, "scoring_criteria": "Score based on future vision clarity (1-5 scale)", "healthcare_focus": "general", "scoring_response": "6\\n\\nThis response provides a comprehensive vision for Lilio's future, detailing its evolution into a leading provider in infant health monitoring technology. It outlines the company\\u2019s strategic roadmap, competitive edge through patent-pending technology, and financial projections indicating robust growth. The analysis also highlights market expansion plans and enhanced service offerings.\\n\\nThe clarity of this future vision is well-supported by specific details about product features, market strategy, and projected outcomes. However, while it touches on clinical validation needs implicitly through its focus on reliability and connectivity, explicit mention of healthcare-specific requirements or regulatory considerations would further strengthen the analysis.\\n\\nOverall, the response effectively communicates a clear and detailed vision for Lilio's future at the end of the investment period, meriting an excellent score within the given criteria."}], "weighted_score": 5.5, "average_score": 5.5, "total_questions": 4, "code_version": "v2.0-with-questions-array"}, "Organization": {"name": "Organization", "key": "organization", "description": "Team, experience, and organizational maturity analysis", "questions": [{"id": 25, "question_id": "org_team", "question_text": "Who are you, what experience do you have?", "response": "Based on the pitch deck content, Lilio appears to be a company focused on infant monitoring technology. The founder, Dr. Nadine Wunderlich, likely brings expertise in healthcare innovation, particularly in pediatric care and wearable health technologies. The emphasis on user experience, as evidenced by the minimalist design of their mobile application interface and product visuals, suggests an understanding of both clinical relevance and consumer needs.\\n\\nThe company's approach to integrating technology into daily routines\\u2014such as monitoring a child\\u2019s vital signs through a wearable device\\u2014indicates a focus on providing peace of mind for parents while ensuring safety. The use of terms like \\"Calm & Safe\\" and \\"Reliable\\" in their messaging underscores the clinical importance of accurate, non-intrusive health tracking.\\n\\nLilio's competitive landscape analysis shows awareness of existing products like Owlet Smart Sock and NeeBo Sensor Bracelet, positioning itself with patent-pending technology. This suggests a strategic focus on innovation within the general healthcare market for infants. The financial projections highlight potential growth in both hardware sales and subscription services, indicating confidence in their product's scalability.\\n\\nOverall, Lilio seems to be leveraging Dr. Wunderlich\\u2019s expertise in pediatric health monitoring technologies to create solutions that are not only clinically relevant but also seamlessly integrated into everyday life, addressing a critical need for parents seeking reliable infant care tools.", "score": 6, "scoring_criteria": "Score based on team experience relevance (1-5 scale)", "healthcare_focus": "general", "scoring_response": "6\\n\\nThis score reflects that the pitch deck provides comprehensive information about Lilio's team experience, particularly highlighting Dr. Nadine Wunderlich\\u2019s expertise in pediatric health monitoring technologies. The analysis indicates her background is highly relevant and aligns well with the company's focus on infant care solutions. While there are no explicit details regarding other team members' experiences or additional clinical validation processes mentioned directly within this section of the pitch deck, the emphasis on Dr. Wunderlich\\u2019s credentials suggests a strong foundation in healthcare innovation.\\n\\nThe presentation effectively communicates how her expertise contributes to creating clinically relevant and user-friendly products for parents seeking reliable infant care tools. The strategic positioning against competitors with patent-pending technology further underscores their innovative approach within this niche market. However, while the pitch deck is robust regarding Dr. Wunderlich\\u2019s role and experience, it could benefit from additional details on broader team expertise or specific clinical validation efforts to achieve a perfect score of 7."}, {"id": 26, "question_id": "org_maturity", "question_text": "How can your organizational maturity be described?", "response": "Based on the pitch deck content, Lilio's organizational maturity can be described as relatively nascent but strategically focused. The company is in an early stage of development, evidenced by its emphasis on design simplicity and user experience, which suggests a strong commitment to creating intuitive products for parents monitoring their infants' health. This focus aligns with current trends towards wearable technology that integrates seamlessly into daily life.\\n\\nLilio's organizational maturity also reflects a clear understanding of the competitive landscape in infant monitoring solutions, as demonstrated by its comparative analysis of existing market offerings like Owlet Smart Sock and NeeBo Sensor Bracelet. The company is positioning itself distinctively through patent-pending technology, indicating an innovative approach to product development.\\n\\nFinancial projections for Lilio show ambitious growth expectations, with significant revenue increases anticipated from both hardware sales and subscription services by 2026. This suggests a well-thought-out business model that leverages recurring income streams alongside initial product purchases.\\n\\nThe presence of a robust advisory board and notable backers further underscores the company's potential maturity in terms of strategic guidance and financial backing. The inclusion of industry experts like Dr. Nadine Wunderlich as founder highlights Lilio\\u2019s commitment to clinical relevance, ensuring their products are grounded in sound medical principles.\\n\\nOverall, while still early in its lifecycle, Lilio demonstrates a mature understanding of market needs, competitive positioning, and growth strategy within the general healthcare focus on infant wellness technology.", "score": 6, "scoring_criteria": "Score based on organizational development level (1-5 scale)", "healthcare_focus": "general", "scoring_response": "6\\n\\nThis analysis provides comprehensive information about Lilio's organizational maturity, covering various aspects such as market positioning, competitive landscape understanding, financial projections, advisory board strength, and clinical relevance. The pitch deck content supports these claims with visual elements that emphasize user experience, design simplicity, and strategic focus on infant wellness technology.\\n\\nThe score reflects the well-rounded nature of the information provided, which aligns with healthcare-specific requirements like clinical validation needs through Dr. Nadine Wunderlich's involvement as founder. While still early in its lifecycle, Lilio demonstrates a mature understanding of market dynamics and growth strategy, justifying an above-average score on the scale."}, {"id": 27, "question_id": "org_structure", "question_text": "How many people are you / pie chart of people per unit?", "response": "Based on the pitch deck content, it appears that the company is focusing on infant monitoring solutions. The slide descriptions emphasize wearable devices for infants, such as wristbands, which monitor vital signs like heart rate and oxygen saturation levels. While there isn't a specific pie chart detailing people per unit directly in the provided slides, we can infer from the context of \\"Aktuelle Werte\\" (current values) that each device is intended to be used by one infant at a time.\\n\\nThe company's product design suggests an individualized approach where each wearable monitors a single child. This aligns with typical healthcare practices for pediatric monitoring devices, which are generally designed for personal use due to the specific and sensitive nature of tracking vital signs in infants. The emphasis on user experience and emotional connection further supports this interpretation, as it highlights personalized care.\\n\\nIn summary, while there is no explicit pie chart or numerical breakdown provided in the slides regarding people per unit, the product's design and focus suggest that each wearable device is intended for one infant at a time. This individualized approach aligns with standard practices in pediatric healthcare monitoring solutions.", "score": 4, "scoring_criteria": "Score based on team structure appropriateness (1-5 scale)", "healthcare_focus": "general", "scoring_response": "4\\n\\nThis score reflects that the pitch deck provides adequate information regarding team structure appropriateness, with some gaps. The analysis indicates an individualized approach for each wearable device intended for one infant at a time, aligning well with standard practices in pediatric healthcare monitoring solutions. However, there is no explicit pie chart or numerical breakdown provided about people per unit directly within the slides. This absence of specific data leaves room for interpretation and some uncertainty regarding team structure appropriateness on a more granular level.\\n\\nThe pitch deck does effectively communicate the product's design focus and its alignment with healthcare practices through contextual clues, which is positive. However, it lacks direct evidence or explicit details that would provide comprehensive insight into how well the team structure supports this individualized approach in terms of clinical validation needs and other specific requirements for pediatric monitoring solutions.\\n\\nOverall, while there are strengths in conveying a clear product focus and alignment with healthcare standards, the lack of detailed quantitative data on people per unit results in some gaps. Thus, it earns a score that reflects good but not comprehensive information coverage regarding team structure appropriateness."}, {"id": 28, "question_id": "org_gaps", "question_text": "What skills are missing in the management team?", "response": "Based on the pitch deck content, several skills appear to be missing in the management team for this healthcare venture focused on infant monitoring technology. Firstly, there is no evident presence of clinical expertise within the leadership team. Given that the product involves critical health metrics such as heart rate and oxygen saturation, having a medical professional or someone with substantial experience in pediatric care would enhance credibility and ensure compliance with regulatory standards.\\n\\nAdditionally, while the pitch deck emphasizes design and user experience, it lacks mention of data privacy and security experts. With wearable devices collecting sensitive health information, expertise in cybersecurity is crucial to protect consumer data and maintain trust.\\n\\nFurthermore, there seems to be a gap in strategic marketing skills tailored specifically for healthcare products. The presence of terms like \\"EINZELHANDEL\\" (retail) and \\"D2C\\" suggests an understanding of direct-to-consumer strategies, but the team may benefit from professionals experienced in navigating complex regulatory environments and effectively communicating health benefits to both consumers and medical practitioners.\\n\\nLastly, while financial projections are included, there is no indication of a CFO or someone with deep experience in healthcare finance. This role would be essential for managing funding rounds, budgeting for R&D, and ensuring sustainable growth within the competitive landscape of infant monitoring solutions.", "score": 4, "scoring_criteria": "Score based on skill gap awareness and planning (1-5 scale)", "healthcare_focus": "general", "scoring_response": "4\\n\\nThis analysis identifies several critical skill gaps in the management team, including clinical expertise, data privacy/security knowledge, strategic marketing skills for healthcare products, and financial acumen specific to healthcare finance. The recognition of these gaps demonstrates an awareness of essential areas that need addressing for a successful venture in infant monitoring technology. However, while it highlights key missing elements, there is limited information on how the team plans to address or fill these gaps. This suggests some planning but not comprehensive strategies are outlined. Therefore, the score reflects adequate identification and partial planning regarding skill gap awareness."}], "weighted_score": 5.0, "average_score": 5.0, "total_questions": 4, "code_version": "v2.0-with-questions-array"}}}]}	gemma3:12b	\N
\.


--
-- Data for Name: gp_template_customizations; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.gp_template_customizations (id, gp_email, base_template_id, customization_name, customized_chapters, customized_questions, customized_weights, is_active, created_at, modified_at) FROM stdin;
\.


--
-- Data for Name: healthcare_sectors; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.healthcare_sectors (id, name, display_name, description, keywords, subcategories, confidence_threshold, regulatory_requirements, is_active, created_at, modified_at) FROM stdin;
1	digital_therapeutics	Digital Therapeutics & Mental Health	Software-based interventions, mental health platforms, addiction treatment apps, and prescription digital therapeutics that deliver clinical outcomes.	["digital therapeutics", "mental health", "DTx", "prescription app", "behavioral intervention", "cognitive therapy", "addiction treatment", "mindfulness", "depression", "anxiety", "PTSD", "therapeutic app", "clinically validated", "FDA cleared", "digital medicine", "behavioral health", "mental wellness", "cognitive behavioral therapy", "CBT", "digital pill", "therapeutic software"]	["Prescription Digital Therapeutics", "Mental Health Platforms", "Addiction Treatment Apps", "Behavioral Intervention Tools", "Cognitive Training Applications"]	0.75	{"fda_required": true, "hipaa_compliance": true, "clinical_validation": true, "evidence_based": true, "patient_outcomes": true}	t	\N	\N
2	healthcare_infrastructure	Healthcare Infrastructure & Workflow	EHR systems, practice management software, revenue cycle management, clinical decision support tools, and administrative automation platforms.	["EHR", "electronic health records", "practice management", "revenue cycle management", "RCM", "clinical decision support", "CDSS", "workflow automation", "administrative automation", "hospital software", "clinic management", "scheduling", "billing", "health information system", "HIS", "practice automation", "medical records", "clinical workflow", "healthcare IT", "health IT"]	["Electronic Health Records", "Practice Management Software", "Revenue Cycle Management", "Clinical Decision Support", "Administrative Automation"]	0.70	{"hipaa_compliance": true, "interoperability": true, "security_compliance": true, "clinical_workflow": true}	t	\N	\N
3	telemedicine	Telemedicine & Remote Care	Virtual consultations, remote monitoring platforms, hospital-at-home solutions, and telehealth infrastructure enabling care delivery outside traditional settings.	["telemedicine", "telehealth", "virtual consultations", "remote monitoring", "RPM", "hospital at home", "virtual care", "remote patient monitoring", "teleconsultation", "digital health platform", "virtual visits", "remote care", "virtual health", "telemonitoring", "remote diagnostics", "virtual clinic", "online consultation", "digital care delivery"]	["Virtual Consultation Platforms", "Remote Patient Monitoring", "Hospital-at-Home Solutions", "Telehealth Infrastructure", "Virtual Care Delivery"]	0.72	{"telehealth_regulations": true, "cross_state_licensing": true, "hipaa_compliance": true, "quality_standards": true}	t	\N	\N
4	diagnostics_devices	Diagnostics & Medical Devices	Point-of-care testing, wearable health monitors, AI-powered diagnostic tools, medical imaging solutions, and next-generation diagnostic technologies.	["diagnostics", "medical device", "point of care", "POC", "wearable", "health monitor", "AI diagnostics", "medical imaging", "diagnostic tools", "biomarker", "lab on chip", "diagnostic platform", "medical technology", "in vitro diagnostics", "IVD", "medical sensor", "health monitoring", "diagnostic testing", "clinical diagnostics", "pathology", "radiology"]	["Point-of-Care Testing", "Wearable Health Monitors", "AI-Powered Diagnostic Tools", "Medical Imaging Solutions", "Next-Generation Diagnostics"]	0.78	{"fda_clearance": true, "ce_marking": true, "clinical_validation": true, "quality_systems": true, "iso_13485": true}	t	\N	\N
5	biotech_pharma	Biotech & Pharmaceuticals	Drug discovery platforms, novel therapeutics, biomarker development, precision medicine tools, and pharmaceutical manufacturing technologies.	["biotech", "pharmaceutical", "drug discovery", "therapeutics", "biomarker", "precision medicine", "pharmaceutical manufacturing", "clinical trials", "molecular diagnostics", "gene therapy", "cell therapy", "biologics", "drug development", "pharmaceutical research", "biomarker discovery", "personalized medicine", "pharmacogenomics", "immunotherapy", "oncology", "rare disease", "orphan drug"]	["Drug Discovery Platforms", "Novel Therapeutics", "Biomarker Development", "Precision Medicine Tools", "Pharmaceutical Manufacturing"]	0.80	{"fda_approval": true, "clinical_trials": true, "gmp_compliance": true, "pharmacovigilance": true, "regulatory_strategy": true}	t	\N	\N
6	health_data_ai	Health Data & AI	Healthcare analytics platforms, AI/ML for clinical applications, population health management, predictive modeling, and clinical research technologies.	["healthcare analytics", "health AI", "machine learning", "clinical AI", "population health", "predictive modeling", "clinical research", "health data platform", "medical AI", "healthcare ML", "clinical decision support", "artificial intelligence", "deep learning", "natural language processing", "NLP", "computer vision", "predictive analytics", "real world evidence", "RWE", "clinical data", "health informatics"]	["Healthcare Analytics Platforms", "AI/ML for Clinical Applications", "Population Health Management", "Predictive Modeling", "Clinical Research Technologies"]	0.75	{"data_privacy": true, "ai_validation": true, "clinical_evidence": true, "algorithmic_transparency": true, "hipaa_compliance": true}	t	\N	\N
7	consumer_health	Consumer Health & Wellness	Direct-to-consumer health services, fitness and nutrition apps, preventive care platforms, and wellness monitoring solutions for healthy populations.	["consumer health", "wellness", "fitness app", "nutrition", "preventive care", "wellness monitoring", "direct to consumer", "DTC", "health tracking", "lifestyle", "wellness platform", "health optimization", "fitness tracking", "nutrition tracking", "wellness coaching", "preventive health", "health and wellness", "lifestyle medicine", "wellness technology", "consumer wellness"]	["Direct-to-Consumer Health Services", "Fitness and Nutrition Apps", "Preventive Care Platforms", "Wellness Monitoring Solutions", "Health Optimization Tools"]	0.65	{"consumer_protection": true, "data_privacy": true, "health_claims": true, "wellness_standards": true}	t	\N	\N
8	healthcare_marketplaces	Healthcare Marketplaces & Access	Provider discovery platforms, healthcare financing solutions, insurance technology, care coordination platforms, and tools improving healthcare accessibility and affordability.	["healthcare marketplace", "provider discovery", "healthcare financing", "insurance technology", "care coordination", "healthcare access", "affordability", "health insurance", "provider network", "healthcare navigation", "health plan", "insurance tech", "insurtech", "healthcare payments", "medical financing", "healthcare affordability", "provider matching", "care navigation", "health benefits", "healthcare commerce"]	["Provider Discovery Platforms", "Healthcare Financing Solutions", "Insurance Technology", "Care Coordination Platforms", "Healthcare Access Tools"]	0.70	{"insurance_regulations": true, "healthcare_compliance": true, "financial_regulations": true, "privacy_protection": true}	t	\N	\N
\.


--
-- Data for Name: healthcare_templates_deprecated; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.healthcare_templates_deprecated (id, template_name, analysis_prompt, description, healthcare_sector_id, is_active, is_default, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: model_configs; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.model_configs (id, model_name, model_type, is_active, created_at, updated_at) FROM stdin;
1	gemma3:12b	vision	t	2025-08-02 21:51:50.765049	2025-08-02 21:51:50.765049
2	gemma3:12b	text	t	2025-08-02 21:51:50.765049	2025-08-02 21:51:50.765049
3	phi4:latest	scoring	t	2025-08-02 21:51:50.765049	2025-08-02 21:51:50.765049
4	phi4:latest	science	t	2025-08-02 21:51:50.765049	2025-08-02 21:51:50.765049
\.


--
-- Data for Name: pipeline_prompts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.pipeline_prompts (id, stage_name, prompt_text, is_active, created_by, created_at, updated_at, prompt_type, prompt_name, is_enabled) FROM stdin;
1	deck_date_extraction	Please identify when this pitch deck was created or last updated. Look for dates in headers, footers, slide timestamps, version information, or any date references that indicate when the deck was prepared. Focus on the most recent date that reflects when the current version was created. Provide the date in a clear format (e.g., 'March 2024', '2024-03-15', 'Q1 2024'). If no date information is available, respond with 'Date not found'.	t	system	2025-08-01 18:11:36.067197	2025-08-01 18:11:36.067197	extraction	Deck Date Extraction	t
2	funding_amount_extraction	Please extract the specific funding amount the startup is seeking from the pitch deck. Look for phrases like 'seeking €X', 'raising $X', 'funding requirement of X', or similar. If you find multiple amounts (seed, Series A, total, etc.), focus on the primary funding amount being sought in this round. Provide only the amount (e.g., '€2.5M', '$500K', '£1M') without additional explanation. If no specific amount is mentioned, respond with 'Not specified'.	t	system	2025-08-01 18:11:36.071451	2025-08-01 18:11:36.071451	extraction	Funding Amount Extraction	t
3	image_analysis	Describe this slide from a pitchdeck from a perspective of an investor, but do not interpret the content. Make sure to include anything notable about it, include text you see in the image, if you see any charts or graphs, describe them in a way that a person that doesn't see them would understand the content. Your style should be rather formal, not colloquial. Do not include any conversational text such as "Okay, here's a detailed description of the image, focusing on the requested aspects:"	t	system	2025-08-01 18:11:36.073235	2025-08-01 18:11:36.073235	extraction	Default Prompt	t
4	offering_extraction	Your task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company. Please do not write any introductory sentences and do not repeat the instruction, just provide what you are asked for.	t	system	2025-08-01 18:11:36.074693	2025-08-01 18:11:36.074693	extraction	Default Prompt	t
5	question_analysis	Your task is to find answers to the following questions: 	t	system	2025-08-01 18:11:36.076292	2025-08-01 18:11:36.076292	extraction	Default Prompt	t
6	role_definition	You are an analyst working at a Venture Capital company. Here is the descriptions of a startup's pitchdeck.	t	system	2025-08-01 18:11:36.077794	2025-08-01 18:11:36.077794	extraction	Default Prompt	t
7	scientific_hypothesis	You are a medical doctor reviewing a pitchdeck of a health startup. Provide a numbered list of core scientific, health related or medical hypothesis that are addressed by the startup. Do not report market size or any other economic hypotheses. Do not mention the name of the product or the company.	t	system	2025-08-01 18:11:36.079262	2025-08-01 18:11:36.079262	extraction	Default Prompt	t
9	startup_name_extraction	Please find the name of the startup in the pitchdeck. Deliver only the name, no conversational text around it.	t	system	2025-08-01 18:11:36.082341	2025-08-01 18:11:36.082341	extraction	Default Prompt	t
8	scoring_analysis	You are a healthcare venture capital analyst scoring a pitch deck analysis.\n\nQuestion: {question_text}\n\nAnalysis Response: {response}\n\nScoring Criteria: {scoring_criteria}\n\nBased on the original pitch deck content and the analysis response, provide a short, single paragraph explaining how you came up with this score. Do NOT repeat the arguments in the anaysis response. After your rationale provide a score from 0-7 where:\n- 0-1: Very poor, missing critical information\n- 2-3: Poor, limited information provided  \n- 4-5: Good, adequate information with some gaps\n- 6-7: Excellent, comprehensive and well-supported information\n\nConsider healthcare-specific requirements and clinical validation needs, but always with the economic viability of this startup idea in mind.\n\nFirst provide your detailed rationale for the score, then end with:\nFinal Score: [X]\n\nOriginal pitch deck content: {pitch_deck_text}	t	system	2025-08-01 18:11:36.080932	2025-08-04 10:16:19.807282	extraction	Default Prompt	t
19	slide_feedback	Analyze this slide for clarity and effectiveness. Focus on:\n\n1. **Visual Clarity**: Can the content be understood in 10 seconds?\n2. **Visual Complexity**: Is the slide cluttered or well-organized?\n3. **Business Case Helpfulness**: Does it effectively communicate its intended message?\n4. **Overall Comprehension**: Would an investor understand the key point quickly?\n\nProvide concise, actionable feedback (2-3 sentences max) that helps improve the slide's effectiveness. Focus on specific issues like:\n- Text readability (too small, too much text)\n- Visual hierarchy problems\n- Unclear messaging or confusing layout\n- Missing context or unclear purpose\n\nIf the slide is clear, well-organized, and effectively communicates its message, respond with exactly "SLIDE_OK".\n\nSlide description: {slide_description}	t	\N	2025-08-05 07:40:06.705977	2025-08-05 07:40:06.705977	\N	\N	t
\.


--
-- Data for Name: pitch_decks; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.pitch_decks (id, user_id, company_id, file_name, file_path, results_file_path, s3_url, processing_status, ai_analysis_results, ai_extracted_startup_name, data_source, zip_filename, created_at, template_processing_results_json, current_processing_task_id) FROM stdin;
98	1	dojo	CSM_Long_Pitch_Deck_March_2025.pdf	projects/dojo/uploads/ef91f6f9287e40a4b2ddb0b740dd9797_CSM_Long_Pitch_Deck_March_2025.pdf	\N	\N	pending	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266371	\N	\N
99	1	dojo	25_07_04_EasyRadiology_Pitch.pdf	projects/dojo/uploads/02222b169c73405d96fbdd1927cb06a4_25_07_04_EasyRadiology_Pitch.pdf	\N	\N	pending	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266385	\N	\N
100	1	dojo	NC Deck AaviGen March 2025.pdf	projects/dojo/uploads/7ec125c8d40c4dd29f4078c6eefac085_NC Deck AaviGen March 2025.pdf	\N	\N	pending	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266391	\N	\N
101	1	dojo	CatMedica_.pdf	projects/dojo/uploads/bcd7cf5116eb4def9e818d0a38f10e16_CatMedica_.pdf	\N	\N	pending	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266396	\N	\N
102	1	dojo	Pitchdeck_MDA.pdf	projects/dojo/uploads/36381c12a42045e98b33a0c0a987e696_Pitchdeck_MDA.pdf	\N	\N	pending	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266402	\N	\N
103	1	dojo	Springboard Health Angels Mar. 20. 2025.pdf	projects/dojo/uploads/9ebb46a7357d4919af41f8df64da08ed_Springboard Health Angels Mar. 20. 2025.pdf	\N	\N	pending	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266407	\N	\N
104	1	dojo	ETERNAL Pitch Deck.pdf	projects/dojo/uploads/e33e7edda45d44879e1d88312c786d45_ETERNAL Pitch Deck.pdf	\N	\N	pending	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266411	\N	\N
105	1	dojo	Final presentation deck 110324.pdf	projects/dojo/uploads/3b14442ba0114b23baa6592fd179eda0_Final presentation deck 110324.pdf	\N	\N	pending	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266416	\N	\N
106	1	dojo	OmniScience Investor Deck Mar 2025.pdf	projects/dojo/uploads/9d725e98c1694e6288a9832c4281b78e_OmniScience Investor Deck Mar 2025.pdf	\N	\N	pending	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266421	\N	\N
107	1	dojo	IM DIHESYS FB.pdf	projects/dojo/uploads/e93deadeaa97480fa9853b2e56fb61ad_IM DIHESYS FB.pdf	\N	\N	pending	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266425	\N	\N
109	1	dojo	Tacit overview Feb 2025.pdf	projects/dojo/uploads/765f47de999940dfb7d5e856536e6ffb_Tacit overview Feb 2025.pdf	\N	\N	pending	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266435	\N	\N
110	1	dojo	Digostics IM Deck 05 25.pdf	projects/dojo/uploads/dabde251be634080b22492d4ef633777_Digostics IM Deck 05 25.pdf	\N	\N	pending	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.26644	\N	\N
111	1	dojo	connectom health.pdf	projects/dojo/uploads/8514179096d0496097b43e0c5cd8f4d7_connectom health.pdf	\N	\N	pending	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266444	\N	\N
112	1	dojo	eversyn_Non-confidential deck_Jan2025.pdf	projects/dojo/uploads/633d24943c084df88fb56477e9ba030f_eversyn_Non-confidential deck_Jan2025.pdf	\N	\N	pending	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266449	\N	\N
113	1	dojo	TernaryTx - Molecular Glues By Design (Q12025).pdf	projects/dojo/uploads/cce2517181dd41338f5945cacab64bb6_TernaryTx - Molecular Glues By Design (Q12025).pdf	\N	\N	pending	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266453	\N	\N
114	1	dojo	testblu_OnePager[2].pdf	projects/dojo/uploads/f8a5b2c4cd5e4092a32918af53345e97_testblu_OnePager[2].pdf	\N	\N	pending	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266458	\N	\N
116	1	dojo	UpLeap_Investor-Presentation_2025-03.pdf	projects/dojo/uploads/39887b321b9f44e198bf8e7511f4656a_UpLeap_Investor-Presentation_2025-03.pdf	\N	\N	pending	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266467	\N	\N
117	1	dojo	Actome_short pitch-deck_March 31st 2025.pptx.pdf	projects/dojo/uploads/0b0de8c745d44d2aa11a5335663a0041_Actome_short pitch-deck_March 31st 2025.pptx.pdf	\N	\N	pending	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266472	\N	\N
118	1	dojo	MovaLife_pitch_202501.pdf	projects/dojo/uploads/964d13dda1ca4b38954234041c632bb6_MovaLife_pitch_202501.pdf	\N	\N	pending	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266476	\N	\N
108	1	dojo	Pharmesol Investment Memo - HGM Advisory.docx.pdf	projects/dojo/uploads/31ccfdf3ba234b98b55430e386b5f8dc_Pharmesol Investment Memo - HGM Advisory.docx.pdf	template_processed	\N	completed	\N	PharmaGenAI\n\n(Note: This name is inferred based on the description of the company's offerings related to generative AI and pharmacy operations.)	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.26643	{"template_analysis": "No chapter analysis available.", "template_used": "Standard Seven-Chapter Review", "processed_at": "2025-08-03T08:17:04.693644", "thumbnails": []}	\N
115	1	dojo	Pitch_radiomics.bio_April2025.pptx.pdf	projects/dojo/uploads/247cf01cbfb94930b416c44442eb58df_Pitch_radiomics.bio_April2025.pptx.pdf	template_processed	\N	completed	\N	Radiomics Bio	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266463	{"template_analysis": "No chapter analysis available.", "template_used": "Standard Seven-Chapter Review", "processed_at": "2025-08-02T21:42:03.322952", "thumbnails": []}	\N
121	1	dojo	company-brief-wikdv.pdf	projects/dojo/uploads/a71af5b2887c4e20a7f91b2d29dba10c_company-brief-wikdv.pdf	results/job_121_1754417039_results.json	\N	failed	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.26649	\N	\N
119	1	dojo	2025_Lilio Investment Deck.pdf	projects/dojo/uploads/4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck.pdf	\N	\N	completed	\N	Lilio	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266481	{"template_analysis": "No chapter analysis available.", "template_used": "Standard Seven-Chapter Review", "processed_at": "2025-08-03T10:57:10.551698", "thumbnails": []}	\N
120	1	dojo	Fusix Biotech_2025v2.pdf	projects/dojo/uploads/30ca13f27ff44fe08fdda5c7e38996e5_Fusix Biotech_2025v2.pdf	\N	\N	completed	\N	\N	dojo	Springboard Health Angels Decks-20250729T074542Z-1-001.zip	2025-08-02 21:38:25.266486	\N	\N
143	12	ismaning	20250310_AskMika_csi.pdf	uploads/ismaning/b0bf6d69-29c5-4c0f-8dd5-e3450511f80f/20250310_AskMika_csi.pdf	\N	\N	completed	\N	\N	startup	\N	2025-08-06 10:33:44.114239	\N	\N
144	12	ismaning	Heartful-Sprout---Pitch-Deck.pdf	uploads/ismaning/6e85c15e-a872-443e-b208-22bbfcbfc0ee/Heartful-Sprout---Pitch-Deck.pdf	\N	\N	failed	\N	\N	startup	\N	2025-08-06 12:21:09.118385	\N	24
138	12	ismaning	Phiggle_PreSend_Slides.pdf	uploads/ismaning/04c6d465-2485-4e8f-b03e-9de7c1e58923/Phiggle_PreSend_Slides.pdf	results/job_138_1754424380_results.json	\N	completed	\N	\N	startup	\N	2025-08-05 20:05:42.857488	\N	7
139	12	ismaning	Oberit-Pitch-Deck-Dec-2024-2.pdf	uploads/ismaning/bdf9e8f9-12e2-44a1-a2bc-8f4b8379a6dc/Oberit-Pitch-Deck-Dec-2024-2.pdf	results/job_139_1754424806_results.json	\N	completed	\N	\N	startup	\N	2025-08-05 20:11:00.722616	\N	8
140	12	ismaning	Apersys_Pitch_non-confidential.pdf	uploads/ismaning/62dcb365-ef28-4b55-ba12-ec676d5a48b4/Apersys_Pitch_non-confidential.pdf	\N	\N	completed	\N	\N	startup	\N	2025-08-05 20:21:02.360939	\N	\N
\.


--
-- Data for Name: processing_progress; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.processing_progress (id, processing_queue_id, step_name, step_status, progress_percentage, message, step_data, created_at) FROM stdin;
1	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:42.097095
2	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:42.10206
3	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:42.137865
4	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:42.141332
5	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:42.173592
6	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:42.179767
7	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:42.221294
8	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:42.230785
9	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:42.280694
10	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:42.286147
11	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:42.336836
12	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:42.345834
13	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:42.420968
14	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:42.430741
15	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:42.513821
16	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:42.519794
17	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:42.609981
18	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:42.615345
19	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:42.698665
20	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:42.70435
21	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:42.790938
22	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:42.797072
23	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:42.860225
24	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:42.865711
25	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:42.925736
26	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:42.930979
27	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:42.995069
28	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:43.001547
29	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:43.067251
30	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:43.073614
31	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:43.154912
32	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:43.160923
33	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:43.246107
34	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:43.250385
35	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:43.285805
36	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:43.290865
37	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:43.349898
38	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:43.354358
39	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:43.417458
40	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:43.421866
41	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:43.500267
42	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:43.504577
43	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:43.536634
44	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:43.540589
45	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:43.601808
46	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:43.606948
47	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:43.667904
48	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:43.674559
49	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:43.738544
50	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:43.744893
51	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:43.807418
52	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:43.813629
53	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:43.876863
54	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:43.883079
55	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:43.945911
56	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:43.950804
57	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:44.036629
58	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:44.040618
59	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:44.087048
60	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:44.091011
61	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:44.134191
62	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:44.141017
63	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:44.218808
64	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:44.222925
65	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:44.25846
66	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:44.262056
67	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:44.294866
68	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:44.29863
69	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:44.331086
70	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:44.334893
71	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:44.368444
72	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:44.371899
73	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:44.439103
74	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:44.444503
75	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:44.507531
76	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:44.512376
77	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:44.576389
78	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:44.581308
79	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:44.642491
80	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:44.648835
81	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:44.717805
82	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:44.723904
83	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:44.787311
84	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:44.79738
85	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:44.863257
86	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:44.869472
87	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:44.934268
88	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:44.939152
89	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:45.001206
90	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:45.006163
91	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:45.083422
92	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:45.089082
93	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:45.167945
94	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:45.173448
95	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:45.208406
96	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:45.214136
97	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:45.296617
98	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:45.300428
99	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:45.343657
100	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:45.347293
101	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:45.393688
102	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:45.398094
103	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:45.443806
104	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:45.448472
105	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:45.492729
106	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:45.497127
107	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:45.541966
108	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:45.546371
109	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:45.592202
110	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:45.597514
111	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:45.642682
112	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:45.650378
113	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:45.694708
114	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:45.699204
115	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:45.743955
116	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:45.748354
117	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:45.792849
118	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:45.797248
119	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:45.841935
120	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:45.846393
121	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:45.891455
122	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:45.898538
123	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:45.94367
124	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:45.948104
125	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:45.991996
126	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:45.996693
127	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:46.042075
128	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:46.047213
129	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:46.095018
130	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:46.106954
131	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:46.151713
132	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:46.156828
133	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:46.203599
134	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:46.210193
135	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:46.257368
136	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:46.261427
137	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:46.305914
138	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:46.309695
139	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:46.353236
140	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:46.357057
141	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:46.400916
142	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:46.405932
143	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:46.450915
144	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:46.455347
145	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:46.499893
146	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:46.504855
147	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:46.551349
148	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:46.559819
149	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:46.608922
150	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:46.612934
151	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:46.65583
152	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:46.659444
153	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:46.701391
154	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:46.704542
155	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:46.747781
156	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:46.75127
157	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:46.805746
158	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:46.810938
159	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:46.862529
160	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:46.866158
161	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:46.900807
162	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:46.904235
163	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:46.948372
164	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:46.952428
165	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:46.996637
166	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.000834
167	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.04525
168	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.049305
169	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.093632
170	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.097616
171	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.141077
172	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.145714
173	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.189452
174	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.193409
175	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.237743
176	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.241988
177	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.286243
178	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.290117
179	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.334535
180	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.338501
181	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.382876
182	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.386909
183	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.431034
184	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.435105
185	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.477434
186	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.48108
187	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.525422
188	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.529254
189	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.573178
190	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.579787
191	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.622468
192	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.627359
193	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.65873
194	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.662416
195	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.734063
196	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.737268
197	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.767876
198	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.771069
199	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.803525
200	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.812893
201	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.844961
202	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.848197
203	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.878082
204	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.881175
205	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.911445
206	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.914776
207	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.945112
208	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.948511
209	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:47.978659
210	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:47.98186
211	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:48.046942
212	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:48.053022
213	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:48.119037
214	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:48.124976
215	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:48.191052
216	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:48.19705
217	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:48.26273
218	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:48.268968
219	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:48.335353
220	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:48.341404
221	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:48.407216
222	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:48.41323
223	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:48.483846
224	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:48.492457
225	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:48.561896
226	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:48.567864
227	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:48.634362
228	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:48.640251
229	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:48.706742
230	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:48.712828
231	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:48.790974
232	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:48.862219
233	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:48.925149
234	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:48.931179
235	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:48.996872
236	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:49.003003
237	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:49.06864
238	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:49.074404
239	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:49.140228
240	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:49.146083
241	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:49.211556
242	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:49.21752
243	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:49.286119
244	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:49.291917
245	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:49.373006
246	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:49.378087
247	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:49.429828
248	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:49.434812
249	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:49.50057
250	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:49.506417
251	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:49.572132
252	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:49.578054
253	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:49.655938
254	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:49.665839
255	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:49.751809
256	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:49.75601
257	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:49.791848
258	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:49.795609
259	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:49.831119
260	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:49.834282
261	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:49.86417
262	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:49.867702
263	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:49.930301
264	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:49.93634
265	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:50.00234
266	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:50.008138
267	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:50.074197
268	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:50.080096
269	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:50.1455
270	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:50.151458
271	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:50.217403
272	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:50.223366
273	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:50.289343
274	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:50.295223
275	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:50.360966
276	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:50.381607
277	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:50.450115
278	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:50.456211
279	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:50.523661
280	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:50.529848
281	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:50.599088
282	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:50.604996
283	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:50.678567
284	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:50.684712
285	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:50.752865
286	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:50.758571
287	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:50.837814
288	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:50.842125
289	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:50.876533
290	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:50.879772
291	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:50.913713
292	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:50.916847
293	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:50.947637
294	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:50.951233
295	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:50.982199
296	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:50.98543
297	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:51.018863
298	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:51.023242
299	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:51.101032
300	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:51.10556
301	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:51.141465
302	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:51.146502
303	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:51.225433
304	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:51.230782
305	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:51.307893
306	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:51.314531
307	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:51.387352
308	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:51.410197
309	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:51.485924
310	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:51.491803
311	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:51.569557
312	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:51.575479
313	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:51.653342
314	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:51.659201
315	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:51.739005
316	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:51.745307
317	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:51.803959
318	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:51.809358
319	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:51.868091
320	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:51.874222
321	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:51.932528
322	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:51.938012
323	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:52.018698
324	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:52.023598
325	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:52.10043
326	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:52.10647
327	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:52.195563
328	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:52.200266
329	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:52.234408
330	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:52.239065
331	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:52.315326
332	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:52.321904
333	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:52.395562
334	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:52.401232
335	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:52.479034
336	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:52.484666
337	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:52.564745
338	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:52.57043
339	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:52.656392
340	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:52.662417
341	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:52.738155
342	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:52.743368
343	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:52.792228
344	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:52.797096
345	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:52.834172
346	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:52.838784
347	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:52.873931
348	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:52.878264
349	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:52.91237
350	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:52.916477
351	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:52.950494
352	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:52.955366
353	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:52.98982
354	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:52.993966
355	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:53.027813
356	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:53.032081
357	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:53.067509
358	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:53.071942
359	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:53.106413
360	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:53.11082
361	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:53.143115
362	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:53.147472
363	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:53.178978
364	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:53.187849
365	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:53.219932
366	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:53.224312
367	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:53.256857
368	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:53.261076
369	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:53.294986
370	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:53.299245
371	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:53.375609
372	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:53.382599
373	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:53.462669
374	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:53.469626
375	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:53.547907
376	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:53.553854
377	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:53.629248
378	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:53.635938
379	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:53.709456
380	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:53.715169
381	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:53.79272
382	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:53.798508
383	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:53.879287
384	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:53.91309
385	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:54.115125
386	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:54.121246
387	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:54.202
388	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:54.207919
389	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:54.285313
390	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:54.290631
391	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:54.349951
392	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:54.355372
393	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:54.434906
394	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:54.440436
395	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:54.518918
396	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:54.524648
397	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:54.602547
398	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:54.608728
399	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:54.68311
400	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:54.68951
401	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:54.767003
402	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:54.773061
403	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:54.864637
404	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:54.869398
405	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:54.917188
406	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:54.922225
407	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:54.957886
408	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:54.964813
409	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:54.995141
410	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:54.998838
411	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:55.067396
412	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:55.073445
413	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:55.138499
414	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:55.144475
415	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:55.209218
416	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:55.215515
417	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:55.282845
418	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:55.288683
419	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:55.353348
420	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:55.359159
421	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:55.424133
422	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:55.430584
423	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:55.496017
424	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:55.501891
425	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:55.568201
426	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:55.574202
427	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:55.639176
428	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:55.645847
429	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:55.710743
430	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:55.716229
431	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:55.781362
432	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:55.787548
433	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:55.852518
434	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:55.857992
435	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:55.922803
436	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:55.928444
437	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:55.994663
438	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:56.00072
439	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:56.066258
440	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:56.072132
441	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:56.137635
442	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:56.143382
443	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:56.208837
444	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:56.214825
445	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:56.280419
446	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:56.286157
447	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:56.351131
448	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:56.357155
449	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:56.422189
450	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:56.428031
451	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:56.493783
452	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:56.499677
453	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:56.564627
454	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:56.570524
455	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:56.636424
456	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:56.64239
457	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:56.708316
458	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:56.714114
459	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:56.779709
460	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:56.785532
461	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:56.851223
462	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:56.857132
463	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:56.922163
464	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:56.928114
465	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:56.994618
466	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:57.000626
467	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:57.068988
468	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:57.07457
469	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:57.14202
470	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:57.147729
471	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:57.213571
472	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:57.219277
473	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:57.284632
474	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:57.290305
475	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:57.354994
476	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:57.360524
477	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:57.425412
478	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:57.431432
479	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:57.497347
480	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:57.503204
481	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:57.568516
482	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:57.574178
483	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:57.63934
484	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:57.645212
485	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:57.711155
486	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:57.717038
487	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:57.783604
488	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:57.789526
489	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:57.854829
490	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:57.860851
491	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:57.928046
492	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:57.933833
493	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:57.99961
494	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:58.005426
495	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:58.07068
496	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:58.076505
497	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:58.141939
498	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:58.147801
499	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:58.212981
500	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:58.218727
501	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:58.287831
502	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:58.293788
503	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:58.359677
504	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:58.365543
505	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:58.43063
506	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:58.436261
507	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:58.503511
508	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:58.537587
509	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:58.636861
510	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:58.642792
511	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:58.707534
512	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:58.715479
513	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:58.780184
514	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:58.785651
515	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:58.854855
516	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:58.862215
517	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:58.927444
518	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:58.93306
519	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:58.997815
520	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:59.003579
521	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:59.069627
522	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:59.07563
523	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:59.141056
524	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:59.146715
525	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:59.212351
526	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:59.218196
527	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:59.292605
528	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:59.30084
529	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:59.381336
530	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:59.384705
531	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:59.414571
532	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:59.417888
533	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:59.482134
534	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:59.487536
535	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:59.552388
536	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:59.55766
537	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:59.622361
538	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:59.628088
539	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:59.692543
540	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:59.69818
541	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:59.762433
542	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:59.768805
543	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:59.83465
544	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:59.840509
545	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:59.905329
546	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:59.910903
547	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:50:59.97623
548	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:50:59.9821
549	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:00.047199
550	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:00.053221
551	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:00.118064
552	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:00.124005
553	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:00.190692
554	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:00.196319
555	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:00.261602
556	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:00.267564
557	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:00.332742
558	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:00.338423
559	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:00.417463
560	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:00.422225
561	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:00.452716
562	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:00.457496
563	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:00.522091
564	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:00.528399
565	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:00.594564
566	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:00.600224
567	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:00.665328
568	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:00.671224
569	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:00.735802
570	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:00.74196
571	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:00.80692
572	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:00.812301
573	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:00.87688
574	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:00.882548
575	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:00.947136
576	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:00.952962
577	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:01.01741
578	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:01.023201
579	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:01.087931
580	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:01.093822
581	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:01.158674
582	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:01.164498
583	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:01.229248
584	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:01.235049
585	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:01.299583
586	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:01.305551
587	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:01.37106
588	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:01.376562
589	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:01.449343
590	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:01.455049
591	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:01.523161
592	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:01.529302
593	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:01.595219
594	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:01.601305
595	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:01.666429
596	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:01.672179
597	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:01.737573
598	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:01.743262
599	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:01.808546
600	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:01.814343
601	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:01.881188
602	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:01.886976
603	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:01.952424
604	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:01.958474
605	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:02.024308
606	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:02.03018
607	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:02.096474
608	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:02.102202
609	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:02.191782
610	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:02.195259
611	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:02.226155
612	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:02.229142
613	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:02.25925
614	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:02.262627
615	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:02.32754
616	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:02.333399
617	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:02.398397
618	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:02.403949
619	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:02.468864
620	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:02.474663
621	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:02.539633
622	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:02.545461
623	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:02.610694
624	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:02.616369
625	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:02.681447
626	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:02.68714
627	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:02.752062
628	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:02.757917
629	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:02.823411
630	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:02.829304
631	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:02.894323
632	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:02.900011
633	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:02.965455
634	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:02.971328
635	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:03.03764
636	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:03.043355
637	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:03.108666
638	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:03.114324
639	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:03.179624
640	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:03.187119
641	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:03.25247
642	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:03.258207
643	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:03.323317
644	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:03.329144
645	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:03.394627
646	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:03.400377
647	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:03.466146
648	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:03.471968
649	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:03.537303
650	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:03.542804
651	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:03.611003
652	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:03.618931
653	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:03.684649
654	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:03.690394
655	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:03.755313
656	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:03.761065
657	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:03.825692
658	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:03.831157
659	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:03.897184
660	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:03.903012
661	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:03.970064
662	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:03.976046
663	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:04.042014
664	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:04.048062
665	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:04.113214
666	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:04.119036
667	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:04.184876
668	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:04.190506
669	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:04.256389
670	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:04.2622
671	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:04.327285
672	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:04.333112
673	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:04.397387
674	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:04.403003
675	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:04.467427
676	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:04.473322
677	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:04.537745
678	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:04.543415
679	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:04.608005
680	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:04.613793
681	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:04.67846
682	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:04.684724
683	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:04.74929
684	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:04.754697
685	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:04.819555
686	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:04.825311
687	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:04.89008
688	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:04.895954
689	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:04.960518
690	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:04.966633
691	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:05.031931
692	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:05.037916
693	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:05.102736
694	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:05.108689
695	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:05.173561
696	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:05.179247
697	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:05.243578
698	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:05.249437
699	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:05.314011
700	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:05.321035
701	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:05.385372
702	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:05.391388
703	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:05.456043
704	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:05.461712
705	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:05.526068
706	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:05.5317
707	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:05.596337
708	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:05.602447
709	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:05.669476
710	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:05.675298
711	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:05.740095
712	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:05.746018
713	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:05.813718
714	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:05.819703
715	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:05.885103
716	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:05.890825
717	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:05.955949
718	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:05.961652
719	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:06.026309
720	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:06.031989
721	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:06.096635
722	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:06.102327
723	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:06.167345
724	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:06.17354
725	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:06.2383
726	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:06.243887
727	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:06.30865
728	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:06.314424
729	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:06.378898
730	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:06.384667
731	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:06.450286
732	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:06.456
733	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:06.521206
734	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:06.527277
735	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:06.592555
736	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:06.598547
737	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:06.66385
738	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:06.669625
739	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:06.734038
740	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:06.739475
741	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:06.804233
742	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:06.81007
743	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:06.874533
744	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:06.880155
745	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:06.945741
746	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:06.951667
747	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:07.017641
748	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:07.023586
749	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:07.089318
750	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:07.095083
751	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:07.16016
752	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:07.166035
753	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:07.231796
754	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:07.237436
755	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:07.31272
756	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:07.317695
757	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:07.388081
758	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:07.393786
759	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:07.45882
760	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:07.464557
761	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:07.535576
762	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:07.541212
763	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:07.612275
764	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:07.617911
765	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:07.688253
766	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:07.693953
767	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:07.766129
768	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:07.772449
769	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:07.865572
770	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:07.869311
771	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:07.916015
772	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:07.919987
773	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:07.95884
774	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:07.96344
775	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:07.9957
776	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:07.999893
777	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.031617
778	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.035607
779	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.066222
780	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.070132
781	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.103486
782	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.107819
783	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.138394
784	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.14364
785	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.174843
786	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.177865
787	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.211164
788	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.215427
789	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.245741
790	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.24873
791	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.27891
792	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.282188
793	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.312161
794	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.315361
795	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.348456
796	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.426171
797	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.459355
798	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.462547
799	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.492199
800	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.496224
801	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.525736
802	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.528659
803	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.561317
804	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.565511
805	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.599218
806	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.603293
807	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.634261
808	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.638383
809	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.669126
810	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.672979
811	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.706921
812	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.711111
813	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.741913
814	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.745675
815	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.776557
816	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.780527
817	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.814153
818	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.818291
819	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.849399
820	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.853469
821	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.887957
822	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.892093
823	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:08.927383
824	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:08.932522
825	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:09.00422
826	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:09.009901
827	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:09.081396
828	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:09.086929
829	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:09.1572
830	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:09.16283
831	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:09.233387
832	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:09.239066
833	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:09.303304
834	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:09.308986
835	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:09.389582
836	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:09.395152
837	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:09.459554
838	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:09.465189
839	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:09.529333
840	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:09.534995
841	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:09.599281
842	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:09.604971
843	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:09.669595
844	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:09.675292
845	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:09.738865
846	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:09.745159
847	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:09.810176
848	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:09.815744
849	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:09.88015
850	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:09.886477
851	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:09.953678
852	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:09.959777
853	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:10.025377
854	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:10.031883
855	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:10.097335
856	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:10.10363
857	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:10.171202
858	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:10.177182
859	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:10.244019
860	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:10.250369
861	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:10.316268
862	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:10.322048
863	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:10.401747
864	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:10.405621
865	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:10.435375
866	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:10.438574
867	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:10.468104
868	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:10.471447
869	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:10.500955
870	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:10.504013
871	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:10.533573
872	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:10.536446
873	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:10.566399
874	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:10.569589
875	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:10.599537
876	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:10.602727
877	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:10.667038
878	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:10.672968
879	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:10.738271
880	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:10.744125
881	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:10.809746
882	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:10.815403
883	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:10.879915
884	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:10.885327
885	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:10.950353
886	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:10.956039
887	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:11.020691
888	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:11.026449
889	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:11.091373
890	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:11.097201
891	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:11.161523
892	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:11.167658
893	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:11.232294
894	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:11.238015
895	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:11.302828
896	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:11.308572
897	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:11.373983
898	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:11.379725
899	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:11.444954
900	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:11.451835
901	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:11.516721
902	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:11.522701
903	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:11.587976
904	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:11.594079
905	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:11.659528
906	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:11.665544
907	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:11.729991
908	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:11.735331
909	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:11.800227
910	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:11.806078
911	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:11.870689
912	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:11.876828
913	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:11.941868
914	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:11.947796
915	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:12.013958
916	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:12.019976
917	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:12.08543
918	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:12.091168
919	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:12.169209
920	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:12.174193
921	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:12.225296
922	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:12.230275
923	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:12.298953
924	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:12.304833
925	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:12.372862
926	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:12.378639
927	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:12.459435
928	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:12.463487
929	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:12.493688
930	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:12.496876
931	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:12.526104
932	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:12.528965
933	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:12.558312
934	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:12.561525
935	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:12.612964
936	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:12.617689
937	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:12.681994
938	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:12.68783
939	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:12.752482
940	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:12.760049
941	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:12.825332
942	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:12.830963
943	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:12.8956
944	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:12.901596
945	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:12.968225
946	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:12.974082
947	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:13.039821
948	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:13.045991
949	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:13.111048
950	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:13.116612
951	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:13.191888
952	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:13.198002
953	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:13.269099
954	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:13.274793
955	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:13.339446
956	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:13.344874
957	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:13.409283
958	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:13.414963
959	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:13.479539
960	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:13.484914
961	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:13.549451
962	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:13.555406
963	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:13.620837
964	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:13.626786
965	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:13.692209
966	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:13.697922
967	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:13.761879
968	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:13.768224
969	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:13.833353
970	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:13.838984
971	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:13.903375
972	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:13.909119
973	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:13.973449
974	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:13.97902
975	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:14.044126
976	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:14.050095
977	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:14.114861
978	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:14.120448
979	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:14.185246
980	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:14.191046
981	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:14.256273
982	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:14.261937
983	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:14.32664
984	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:14.332556
985	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:14.39745
986	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:14.403357
987	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:14.471834
988	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:14.477965
989	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:14.542812
990	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:14.54864
991	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:14.613523
992	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:14.619182
993	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:14.683923
994	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:14.689563
995	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:14.753961
996	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:14.75954
997	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:14.824323
998	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:14.829674
999	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:14.895146
1000	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:14.902262
1001	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:14.967536
1002	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:14.973562
1003	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:15.038832
1004	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:15.044554
1005	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:15.109806
1006	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:15.115807
1007	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:15.181262
1008	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:15.186886
1009	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:15.251675
1010	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:15.257445
1011	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:15.32223
1012	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:15.328347
1013	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:15.39333
1014	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:15.3987
1015	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:15.46407
1016	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:15.469899
1017	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:15.5346
1018	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:15.540018
1019	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:15.605234
1020	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:15.613552
1021	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:15.67854
1022	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:15.684261
1023	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:15.749199
1024	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:15.754984
1025	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:15.820099
1026	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:15.825742
1027	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:15.890412
1028	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:15.895925
1029	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:15.961383
1030	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:15.967047
1031	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:16.032329
1032	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:16.0381
1033	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:16.103245
1034	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:16.108924
1035	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:16.17383
1036	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:16.179702
1037	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:16.246561
1038	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:16.256921
1039	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:16.333717
1040	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:16.339104
1041	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:16.410703
1042	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:16.41646
1043	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:16.499736
1044	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:16.506011
1045	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:16.58465
1046	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:16.589451
1047	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:16.636008
1048	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:16.639925
1049	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:16.676934
1050	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:16.680011
1051	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:16.70953
1052	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:16.712389
1053	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:16.74179
1054	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:16.744419
1055	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:16.773526
1056	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:16.776221
1057	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:16.808558
1058	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:16.81163
1059	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:16.840878
1060	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:16.84389
1061	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:16.873225
1062	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:16.877071
1063	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:16.910894
1064	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:16.915194
1065	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:16.946275
1066	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:16.950362
1067	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:16.984002
1068	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:16.988321
1069	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:17.020206
1070	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:17.025085
1071	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:17.05622
1072	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:17.060461
1073	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:17.091461
1074	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:17.095715
1075	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:17.126556
1076	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:17.130951
1077	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:17.164969
1078	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:17.169364
1079	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:17.200619
1080	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:17.204917
1081	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:17.235471
1082	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:17.239825
1083	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:17.300842
1084	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:17.308735
1085	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:17.372811
1086	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:17.378176
1087	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:17.442539
1088	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:17.448489
1089	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:17.512674
1090	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:17.518291
1091	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:17.582362
1092	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:17.587978
1093	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:17.652396
1094	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:17.658071
1095	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:17.72206
1096	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:17.727879
1097	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:17.792112
1098	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:17.79766
1099	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:17.862075
1100	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:17.868525
1101	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:17.933433
1102	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:17.939182
1103	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:18.003606
1104	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:18.009169
1105	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:18.073216
1106	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:18.078777
1107	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:18.142943
1108	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:18.148813
1109	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:18.212827
1110	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:18.218256
1111	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:18.282684
1112	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:18.288169
1113	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:18.351967
1114	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:18.357578
1115	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:18.421351
1116	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:18.42656
1117	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:18.49069
1118	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:18.496607
1119	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:18.561682
1120	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:18.567214
1121	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:18.631672
1122	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:18.637798
1123	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:18.702543
1124	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:18.709034
1125	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:18.777818
1126	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:18.782959
1127	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:18.853504
1128	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:18.85786
1129	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:18.920599
1130	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:18.926366
1131	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:18.99502
1132	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:19.001187
1133	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:19.065842
1134	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:19.071456
1135	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:19.135386
1136	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:19.141087
1137	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:19.205186
1138	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:19.210715
1139	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:19.280731
1140	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:19.286604
1141	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:19.367737
1142	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:19.373745
1143	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:19.439247
1144	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:19.445395
1145	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:19.512
1146	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:19.518091
1147	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:19.583649
1148	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:19.589607
1149	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:19.654892
1150	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:19.660959
1151	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:19.72679
1152	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:19.732565
1153	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:19.798077
1154	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:19.804045
1155	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:19.869694
1156	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:19.875824
1157	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:19.941198
1158	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:19.94706
1159	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.015619
1160	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.02158
1161	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.08774
1162	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.093483
1163	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.159119
1164	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.164939
1165	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.230636
1166	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.236491
1167	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.302035
1168	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.308067
1169	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.393368
1170	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.393368
1171	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.422993
1172	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.426253
1173	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.456194
1174	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.459393
1175	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.488619
1176	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.491695
1177	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.521731
1178	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.524868
1179	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.554437
1180	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.557507
1181	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.586916
1182	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.58997
1183	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.620224
1184	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.623474
1185	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.653438
1186	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.656658
1187	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.686382
1188	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.68937
1189	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.71955
1190	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.72256
1191	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.75313
1192	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.756415
1193	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.786
1194	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.788907
1195	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.820127
1196	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.823277
1197	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.853274
1198	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.856364
1199	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.887716
1200	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.890904
1201	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.920922
1202	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.924139
1203	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.956834
1204	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.960103
1205	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:20.991789
1206	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:20.994899
1207	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.024987
1208	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.02812
1209	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.058112
1210	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.061266
1211	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.093987
1212	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.09747
1213	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.128407
1214	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.131452
1215	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.161323
1216	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.164415
1217	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.194225
1218	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.197235
1219	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.227242
1220	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.230297
1221	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.260371
1222	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.26343
1223	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.293145
1224	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.295994
1225	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.326111
1226	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.329256
1227	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.358932
1228	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.362959
1229	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.393299
1230	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.396076
1231	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.425441
1232	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.428209
1233	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.458275
1234	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.461358
1235	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.491616
1236	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.494862
1237	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.525092
1238	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.528268
1239	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.558785
1240	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.562158
1241	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.592371
1242	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.595548
1243	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.62609
1244	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.629301
1245	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.659856
1246	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.662946
1247	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.692654
1248	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.695793
1249	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.725524
1250	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.728248
1251	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.758074
1252	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.761109
1253	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.7905
1254	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.793229
1255	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.823199
1256	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.826334
1257	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.856054
1258	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.859185
1259	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.888844
1260	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.891553
1261	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.920797
1262	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.923693
1263	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.953908
1264	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.957194
1265	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:21.988042
1266	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:21.991167
1267	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.020598
1268	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.02346
1269	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.053695
1270	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.056783
1271	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.086473
1272	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.089213
1273	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.13279
1274	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.13568
1275	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.165651
1276	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.168891
1277	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.198943
1278	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.202034
1279	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.231677
1280	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.234351
1281	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.268373
1282	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.271478
1283	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.30198
1284	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.305112
1285	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.335191
1286	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.338327
1287	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.368895
1288	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.372299
1289	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.402506
1290	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.405535
1291	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.436129
1292	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.439335
1293	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.4691
1294	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.471866
1295	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.501214
1296	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.504152
1297	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.534368
1298	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.537418
1299	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.568118
1300	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.571184
1301	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.601211
1302	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.604447
1303	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.634509
1304	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.637625
1305	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.667583
1306	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.670684
1307	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.700535
1308	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.703415
1309	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.732859
1310	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.73558
1311	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.76573
1312	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.769024
1313	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.798774
1314	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.801786
1315	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.831854
1316	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.834945
1317	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.864871
1318	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.867704
1319	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.897777
1320	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.900951
1321	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.930594
1322	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.933371
1323	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.964091
1324	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:22.967329
1325	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:22.997882
1326	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.000969
1327	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.032552
1328	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.035773
1329	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.065645
1330	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.068717
1331	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.099111
1332	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.102228
1333	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.135481
1334	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.140657
1335	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.172522
1336	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.175781
1337	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.206436
1338	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.209607
1339	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.23974
1340	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.242876
1341	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.273213
1342	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.276345
1343	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.30632
1344	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.309486
1345	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.339694
1346	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.342727
1347	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.372389
1348	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.375297
1349	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.420067
1350	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.4233
1351	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.452745
1352	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.455472
1353	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.485219
1354	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.488394
1355	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.518393
1356	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.521993
1357	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.552306
1358	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.555306
1359	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.585877
1360	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.589654
1361	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.620466
1362	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.624455
1363	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.656866
1364	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.66094
1365	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.692161
1366	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.69597
1367	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.727058
1368	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.73102
1369	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.76153
1370	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.765184
1371	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.79652
1372	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.801477
1373	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.832454
1374	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.836064
1375	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.866551
1376	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.870341
1377	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.901151
1378	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.905141
1379	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.935666
1380	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.939432
1381	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:23.971345
1382	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:23.975418
1383	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:24.00724
1384	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:24.011738
1385	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:24.043641
1386	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:24.047536
1387	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:24.078218
1388	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:24.081889
1389	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:24.112359
1390	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:24.116204
1391	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:24.147201
1392	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:24.151102
1393	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:24.181656
1394	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:24.185429
1395	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:24.21582
1396	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:24.21958
1397	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:24.250124
1398	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:24.254808
1399	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:24.287925
1400	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:24.29186
1401	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:24.322932
1402	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:24.327182
1403	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:24.392471
1404	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:24.397962
1405	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:24.462324
1406	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:24.467527
1407	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:24.532063
1408	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:24.537747
1409	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:24.60272
1410	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:24.608424
1411	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:24.673986
1412	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:24.679564
1413	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:24.744199
1414	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:24.749692
1415	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:24.814014
1416	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:24.81932
1417	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:24.884244
1418	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:24.889923
1419	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:24.957058
1420	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:24.962586
1421	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:25.039163
1422	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:25.044798
1423	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:25.115729
1424	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:25.121891
1425	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:25.214296
1426	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:25.219453
1427	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:25.267111
1428	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:25.271933
1429	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:25.328282
1430	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:25.334616
1431	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:25.401023
1432	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:25.406955
1433	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:25.471086
1434	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:25.476821
1435	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:25.540817
1436	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:25.546233
1437	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:25.610726
1438	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:25.616241
1439	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:25.680978
1440	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:25.687274
1441	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:25.752227
1442	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:25.757812
1443	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:25.822245
1444	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:25.828063
1445	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:25.892021
1446	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:25.898336
1447	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:25.963605
1448	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:25.970046
1449	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:26.036135
1450	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:26.042466
1451	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:26.107548
1452	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:26.113141
1453	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:26.177629
1454	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:26.183208
1455	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:26.247216
1456	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:26.25281
1457	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:26.316865
1458	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:26.322403
1459	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:26.386246
1460	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:26.39194
1461	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:26.45649
1462	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:26.462135
1463	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:26.526174
1464	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:26.531677
1465	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:26.596934
1466	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:26.602796
1467	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:26.667681
1468	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:26.673634
1469	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:26.738187
1470	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:26.74379
1471	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:26.808548
1472	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:26.814208
1473	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:26.878203
1474	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:26.88383
1475	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:26.948716
1476	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:26.954377
1477	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:27.019409
1478	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:27.025199
1479	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:27.089499
1480	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:27.095678
1481	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:27.161159
1482	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:27.168947
1483	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:27.234392
1484	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:27.240924
1485	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:27.306355
1486	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:27.311903
1487	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:27.376498
1488	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:27.382574
1489	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:27.452816
1490	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:27.459254
1491	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:27.529442
1492	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:27.535454
1493	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:27.599967
1494	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:27.605903
1495	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:27.670535
1496	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:27.676379
1497	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:27.741454
1498	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:27.748011
1499	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:27.812686
1500	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:27.818324
1501	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:27.882962
1502	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:27.888847
1503	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:27.953083
1504	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:27.958863
1505	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:28.024663
1506	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:28.030437
1507	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:28.095867
1508	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:28.101639
1509	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:28.166149
1510	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:28.171922
1511	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:28.236487
1512	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:28.243086
1513	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:28.312439
1514	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:28.318079
1515	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:28.383129
1516	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:28.390538
1517	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:28.455561
1518	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:28.461595
1519	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:28.525924
1520	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:28.531369
1521	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:28.596151
1522	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:28.602151
1523	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:28.667257
1524	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:28.673196
1525	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:28.738422
1526	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:28.744102
1527	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:28.80885
1528	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:28.814651
1529	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:28.879378
1530	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:28.885148
1531	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:28.949826
1532	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:28.955554
1533	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:29.020703
1534	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:29.026613
1535	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:29.091933
1536	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:29.097685
1537	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:29.162197
1538	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:29.168341
1539	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:29.233492
1540	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:29.301523
1541	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:29.391515
1542	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:29.397545
1543	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:29.478476
1544	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:29.484872
1545	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:29.570482
1546	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:29.575083
1547	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:29.61885
1548	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:29.623786
1549	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:29.666972
1550	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:29.670809
1551	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:29.735138
1552	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:29.740914
1553	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:29.805981
1554	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:29.81171
1555	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:29.876033
1556	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:29.881602
1557	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:29.945718
1558	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:29.951316
1559	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:30.023852
1560	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:30.030583
1561	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:30.09507
1562	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:30.100888
1563	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:30.165188
1564	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:30.170967
1565	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:30.240959
1566	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:30.248166
1567	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:30.327672
1568	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:30.333299
1569	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:30.398013
1570	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:30.403707
1571	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:30.468562
1572	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:30.474159
1573	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:30.538727
1574	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:30.544295
1575	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:30.608969
1576	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:30.615033
1577	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:30.680967
1578	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:30.686607
1579	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:30.75139
1580	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:30.757203
1581	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:30.821356
1582	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:30.826776
1583	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:30.891907
1584	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:30.89828
1585	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:30.963707
1586	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:30.970246
1587	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:31.035709
1588	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:31.041595
1589	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:31.106681
1590	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:31.112701
1591	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:31.177666
1592	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:31.183313
1593	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:31.251585
1594	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:31.257813
1595	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:31.322392
1596	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:31.32941
1597	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:31.393914
1598	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:31.401241
1599	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:31.465898
1600	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:31.471934
1601	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:31.537931
1602	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:31.543635
1603	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:31.608506
1604	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:31.614118
1605	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:31.67864
1606	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:31.685118
1607	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:31.749972
1608	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:31.754677
1609	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:31.827182
1610	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:31.831573
1611	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:31.894954
1612	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:31.900806
1613	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:31.965832
1614	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:31.97253
1615	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:32.037545
1616	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:32.043125
1617	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:32.123468
1618	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:32.127971
1619	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:32.179488
1620	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:32.186011
1621	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:32.250386
1622	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:32.262934
1623	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:32.327437
1624	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:32.333481
1625	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:32.397857
1626	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:32.403336
1627	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:32.468315
1628	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:32.474058
1629	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:32.538321
1630	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:32.543966
1631	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:32.608585
1632	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:32.614391
1633	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:32.679062
1634	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:32.685021
1635	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:32.749585
1636	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:32.755731
1637	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:32.82131
1638	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:32.826973
1639	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:32.892308
1640	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:32.897979
1641	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:32.962534
1642	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:32.968272
1643	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:33.033519
1644	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:33.039527
1645	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:33.104333
1646	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:33.109993
1647	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:33.174849
1648	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:33.180846
1649	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:33.245299
1650	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:33.250894
1651	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:33.315568
1652	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:33.321243
1653	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:33.386053
1654	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:33.391722
1655	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:33.456104
1656	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:33.461553
1657	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:33.526104
1658	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:33.531897
1659	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:33.596282
1660	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:33.604033
1661	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:33.669251
1662	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:33.674942
1663	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:33.739312
1664	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:33.745083
1665	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:33.809664
1666	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:33.815143
1667	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:33.879518
1668	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:33.88558
1669	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:33.951527
1670	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:33.957305
1671	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:34.023038
1672	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:34.029085
1673	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:34.093493
1674	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:34.099293
1675	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:34.17781
1676	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:34.181987
1677	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:34.247669
1678	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:34.255196
1679	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:34.32129
1680	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:34.327049
1681	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:34.392863
1682	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:34.398491
1683	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:34.462827
1684	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:34.469099
1685	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:34.533127
1686	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:34.538598
1687	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:34.603145
1688	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:34.609022
1689	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:34.673781
1690	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:34.6796
1691	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:34.743905
1692	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:34.749814
1693	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:34.813602
1694	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:34.81918
1695	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:34.884059
1696	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:34.890003
1697	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:34.955036
1698	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:34.960669
1699	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:35.025534
1700	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:35.031267
1701	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:35.095613
1702	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:35.10144
1703	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:35.165469
1704	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:35.171292
1705	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:35.235584
1706	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:35.241264
1707	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:35.305553
1708	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:35.311432
1709	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:35.375392
1710	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:35.380961
1711	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:35.444915
1712	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:35.450633
1713	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:35.514665
1714	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:35.520218
1715	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:35.584332
1716	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:35.589955
1717	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:35.654169
1718	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:35.66002
1719	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:35.724613
1720	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:35.730437
1721	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:35.795026
1722	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:35.800706
1723	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:35.865081
1724	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:35.870811
1725	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:35.93526
1726	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:35.941012
1727	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:36.005448
1728	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:36.011236
1729	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:36.078844
1730	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:36.084796
1731	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:36.151804
1732	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:36.157951
1733	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:36.223458
1734	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:36.229185
1735	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:36.293383
1736	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:36.299179
1737	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:36.363146
1738	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:36.368606
1739	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:36.432819
1740	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:36.440499
1741	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:36.505136
1742	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:36.511003
1743	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:36.575533
1744	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:36.581459
1745	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:36.646166
1746	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:36.651877
1747	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:36.716091
1748	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:36.722043
1749	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:36.787231
1750	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:36.79301
1751	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:36.856937
1752	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:36.862455
1753	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:36.927246
1754	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:36.933164
1755	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:36.998131
1756	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:37.004177
1757	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:37.070461
1758	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:37.07631
1759	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:37.148299
1760	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:37.154021
1761	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:37.219905
1762	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:37.225556
1763	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:37.298214
1764	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:37.30388
1765	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:37.380877
1766	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:37.38654
1767	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:37.45128
1768	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:37.457009
1769	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:37.528058
1770	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:37.533786
1771	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:37.602671
1772	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:37.60925
1773	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:37.674531
1774	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:37.680164
1775	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:37.750922
1776	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:37.756442
1777	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:37.821212
1778	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:37.826867
1779	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:37.897223
1780	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:37.903013
1781	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:37.98143
1782	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:37.987383
1783	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.057659
1784	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.063289
1785	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.153587
1786	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.158303
1787	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.205556
1788	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.210337
1789	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.255864
1790	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.260605
1791	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.298177
1792	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.302959
1793	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.333074
1794	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.33627
1795	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.366165
1796	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.369058
1797	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.401873
1798	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.405136
1799	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.434744
1800	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.437605
1801	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.467386
1802	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.47039
1803	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.50028
1804	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.504432
1805	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.537509
1806	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.540527
1807	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.570048
1808	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.572857
1809	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.602729
1810	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.606133
1811	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.636094
1812	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.639661
1813	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.669916
1814	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.672958
1815	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.70309
1816	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.706394
1817	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.735956
1818	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.738733
1819	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.77149
1820	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.774658
1821	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.804317
1822	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.807354
1823	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.837069
1824	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.840124
1825	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.873703
1826	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.87777
1827	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.907677
1828	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.91097
1829	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.942093
1830	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.947133
1831	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:38.98163
1832	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:38.986775
1833	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.018692
1834	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.023092
1835	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.056952
1836	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.061123
1837	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.092807
1838	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.096964
1839	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.130888
1840	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.135196
1841	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.166236
1842	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.170548
1843	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.201999
1844	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.206068
1845	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.236632
1846	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.241096
1847	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.287538
1848	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.2919
1849	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.322809
1850	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.326726
1851	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.357534
1852	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.362224
1853	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.393322
1854	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.397311
1855	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.428104
1856	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.431955
1857	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.46895
1858	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.474197
1859	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.544903
1860	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.549813
1861	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.619787
1862	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.624785
1863	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.654536
1864	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.657995
1865	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.726173
1866	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.731271
1867	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.762249
1868	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.766406
1869	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.797652
1870	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.802532
1871	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.873937
1872	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.879592
1873	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:39.944393
1874	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:39.949954
1875	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:40.026823
1876	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:40.032822
1877	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:40.10541
1878	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:40.110954
1879	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:40.178987
1880	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:40.184671
1881	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:40.26907
1882	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:40.275462
1883	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:40.373378
1884	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:40.377428
1885	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:40.423869
1886	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:40.429242
1887	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:40.469734
1888	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:40.476125
1889	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:40.542817
1890	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:40.548534
1891	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:40.620165
1892	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:40.626811
1893	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:40.691354
1894	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:40.697088
1895	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:40.766486
1896	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:40.772135
1897	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:40.84303
1898	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:40.848644
1899	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:40.913177
1900	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:40.918988
1901	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:40.990129
1902	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:40.995686
1903	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:41.072428
1904	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:41.076684
1905	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:41.109322
1906	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:41.11262
1907	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:41.142832
1908	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:41.146989
1909	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:41.219941
1910	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:41.225996
1911	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:41.277573
1912	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:41.283348
1913	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:41.35445
1914	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:41.360268
1915	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:41.426146
1916	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:41.43253
1917	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:41.497981
1918	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:41.503532
1919	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:41.575564
1920	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:41.581541
1921	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:41.652532
1922	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:41.658298
1923	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:41.728995
1924	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:41.734866
1925	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:41.805812
1926	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:41.811814
1927	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:41.876828
1928	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:41.882702
1929	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:41.953196
1930	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:41.959046
1931	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:42.039826
1932	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:42.045229
1933	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:42.127213
1934	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:42.131553
1935	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:42.20473
1936	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:42.210999
1937	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:42.282126
1938	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:42.287709
1939	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:42.357746
1940	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:42.363788
1941	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:42.434479
1942	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:42.440436
1943	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:42.506104
1944	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:42.5122
1945	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:42.580628
1946	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:42.586598
1947	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:42.661797
1948	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:42.671217
1949	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:42.737688
1950	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:42.74359
1951	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:42.810571
1952	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:42.816301
1953	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:42.881011
1954	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:42.886944
1955	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:42.955507
1956	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:42.961585
1957	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:43.028565
1958	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:43.034549
1959	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:43.10336
1960	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:43.109703
1961	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:43.176135
1962	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:43.182052
1963	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:43.254734
1964	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:43.261674
1965	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:43.327972
1966	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:43.333506
1967	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:43.398584
1968	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:43.404084
1969	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:43.469086
1970	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:43.474686
1971	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:43.540086
1972	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:43.545714
1973	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:43.610308
1974	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:43.616074
1975	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:43.681172
1976	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:43.686862
1977	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:43.751827
1978	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:43.757598
1979	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:43.82227
1980	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:43.827891
1981	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:43.893361
1982	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:43.899025
1983	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:43.964125
1984	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:43.970282
1985	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:44.035206
1986	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:44.040936
1987	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:44.10611
1988	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:44.111894
1989	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:44.177235
1990	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:44.183575
1991	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:44.250084
1992	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:44.2558
1993	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:44.320485
1994	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:44.326069
1995	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:44.405272
1996	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:44.411039
1997	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:44.477177
1998	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:44.483088
1999	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:44.547858
2000	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:44.553577
2001	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:44.618156
2002	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:44.624083
2003	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:44.68904
2004	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:44.69501
2005	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:44.766255
2006	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:44.772236
2007	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:44.84024
2008	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:44.846001
2009	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:44.910826
2010	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:44.916587
2011	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:44.981593
2012	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:44.987164
2013	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:45.051965
2014	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:45.057723
2015	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:45.12271
2016	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:45.160511
2017	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:45.226369
2018	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:45.232133
2019	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:45.303498
2020	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:45.309348
2021	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:45.381147
2022	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:45.386715
2023	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:45.459072
2024	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:45.464625
2025	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:45.535817
2026	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:45.541548
2027	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:45.607531
2028	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:45.61401
2029	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:45.680442
2030	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:45.68606
2031	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:45.758055
2032	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:45.764684
2033	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:45.831022
2034	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:45.836427
2035	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:45.908081
2036	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:45.913937
2037	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:45.986678
2038	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:45.99229
2039	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:46.065105
2040	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:46.072036
2041	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:46.144675
2042	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:46.150252
2043	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:46.219949
2044	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:46.226044
2045	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:46.291169
2046	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:46.297012
2047	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:46.368041
2048	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:46.373789
2049	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:46.438136
2050	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:46.443625
2051	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:46.514949
2052	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:46.520526
2053	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:46.592038
2054	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:46.597082
2055	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:46.62969
2056	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:46.633
2057	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:46.662559
2058	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:46.666802
2059	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:46.73957
2060	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:46.745054
2061	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:46.825524
2062	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:46.830324
2063	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:46.895031
2064	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:46.899948
2065	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:46.940862
2066	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:46.947098
2067	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:47.025104
2068	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:47.030641
2069	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:47.100915
2070	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:47.106448
2071	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:47.171684
2072	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:47.1774
2073	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:47.253532
2074	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:47.259591
2075	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:47.331567
2076	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:47.337365
2077	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:47.402575
2078	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:47.408325
2079	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:47.479313
2080	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:47.485137
2081	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:47.556583
2082	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:47.56471
2083	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:47.635173
2084	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:47.641041
2085	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:47.711987
2086	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:47.717677
2087	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:47.783101
2088	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:47.789784
2089	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:47.855491
2090	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:47.86122
2091	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:47.934277
2092	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:47.941939
2093	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:48.015128
2094	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:48.020826
2095	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:48.090256
2096	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:48.095932
2097	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:48.167358
2098	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:48.173056
2099	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:48.24248
2100	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:48.248092
2101	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:48.319121
2102	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:48.32465
2103	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:48.392953
2104	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:48.399459
2105	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:48.463939
2106	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:48.469549
2107	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:48.54141
2108	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:48.547101
2109	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:48.611497
2110	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:48.617308
2111	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:48.688314
2112	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:48.694089
2113	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:48.764675
2114	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:48.770376
2115	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:48.839977
2116	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:48.845994
2117	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:48.916596
2118	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:48.922945
2119	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:49.016296
2120	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:49.021531
2121	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:49.087454
2122	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:49.093507
2123	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:49.165133
2124	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:49.171697
2125	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:49.237303
2126	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:49.243265
2127	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:49.333695
2128	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:49.339525
2129	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:49.403449
2130	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:49.409041
2131	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:49.473272
2132	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:49.478924
2133	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:49.542975
2134	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:49.549427
2135	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:49.614246
2136	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:49.619945
2137	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:49.684266
2138	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:49.690026
2139	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:49.754114
2140	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:49.759903
2141	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:49.824077
2142	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:49.829774
2143	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:49.893523
2144	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:49.898949
2145	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:49.963832
2146	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:49.970622
2147	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:50.037089
2148	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:50.042734
2149	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:50.106676
2150	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:50.112295
2151	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:50.17701
2152	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:50.182885
2153	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:50.247293
2154	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:50.252578
2155	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:50.329397
2156	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:50.334873
2157	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:50.387554
2158	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:50.394011
2159	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:50.460607
2160	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:50.466137
2161	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:50.530266
2162	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:50.535938
2163	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:50.600498
2164	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:50.60641
2165	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:50.671227
2166	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:50.677227
2167	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:50.741825
2168	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:50.747505
2169	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:50.812939
2170	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:50.818519
2171	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:50.88337
2172	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:50.889152
2173	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:50.962345
2174	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:50.968077
2175	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:51.039683
2176	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:51.045731
2177	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:51.115529
2178	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:51.121637
2179	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:51.213691
2180	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:51.218722
2181	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:51.266283
2182	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:51.27291
2183	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:51.313245
2184	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:51.31782
2185	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:51.387959
2186	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:51.393641
2187	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:51.464924
2188	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:51.470792
2189	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:51.536146
2190	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:51.542586
2191	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:51.614095
2192	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:51.619917
2193	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:51.690947
2194	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:51.696648
2195	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:51.761262
2196	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:51.766573
2197	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:51.837644
2198	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:51.843391
2199	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:51.915023
2200	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:51.92079
2201	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:51.998026
2202	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:52.003688
2203	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:52.09031
2204	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:52.093479
2205	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:52.12339
2206	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:52.128122
2207	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:52.200111
2208	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:52.205917
2209	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:52.271435
2210	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:52.277813
2211	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:52.343834
2212	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:52.349801
2213	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:52.420115
2214	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:52.425726
2215	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:52.491186
2216	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:52.497623
2217	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:52.569358
2218	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:52.574931
2219	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:52.644624
2220	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:52.65133
2221	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:52.716944
2222	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:52.722522
2223	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:52.793789
2224	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:52.799688
2225	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:52.864897
2226	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:52.870485
2227	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:52.940475
2228	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:52.946021
2229	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:53.017708
2230	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:53.023197
2231	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:53.094347
2232	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:53.100887
2233	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:53.171845
2234	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:53.177453
2235	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:53.241795
2236	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:53.250048
2237	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:53.314829
2238	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:53.321303
2239	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:53.386408
2240	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:53.392606
2241	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:53.460685
2242	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:53.46766
2243	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:53.550838
2244	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:53.555551
2245	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:53.586324
2246	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:53.592252
2247	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:53.657995
2248	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:53.663924
2249	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:53.728326
2250	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:53.733956
2251	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:53.797737
2252	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:53.803006
2253	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:53.869183
2254	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:53.874721
2255	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:53.938728
2256	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:53.944215
2257	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:54.009073
2258	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:54.014959
2259	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:54.079357
2260	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:54.085314
2261	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:54.149686
2262	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:54.155269
2263	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:54.219923
2264	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:54.225613
2265	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:54.289413
2266	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:54.297242
2267	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:54.361443
2268	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:54.367172
2269	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:54.431916
2270	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:54.438354
2271	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:54.504551
2272	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:54.51036
2273	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:54.574658
2274	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:54.580253
2275	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:54.644567
2276	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:54.650964
2277	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:54.716839
2278	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:54.722502
2279	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:54.787138
2280	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:54.793873
2281	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:54.859251
2282	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:54.864844
2283	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:54.929613
2284	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:54.935468
2285	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:55.000848
2286	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:55.006377
2287	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:55.070976
2288	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:55.076503
2289	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:55.140552
2290	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:55.146541
2291	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:55.212182
2292	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:55.217783
2293	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:55.282736
2294	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:55.2883
2295	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:55.353969
2296	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:55.360137
2297	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:55.44603
2298	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:55.453624
2299	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:55.549588
2300	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:55.55335
2301	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:55.600844
2302	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:55.604679
2303	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:55.64535
2304	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:55.649621
2305	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:55.682055
2306	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:55.685991
2307	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:55.716642
2308	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:55.721297
2309	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:55.77828
2310	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:55.783333
2311	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:55.836918
2312	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:55.842021
2313	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:55.90019
2314	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:55.905376
2315	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:55.958654
2316	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:55.963905
2317	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:56.024791
2318	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:56.029873
2319	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:56.082636
2320	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:56.087801
2321	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:56.145807
2322	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:56.150903
2323	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:56.205136
2324	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:56.210113
2325	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:56.266706
2326	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:56.271852
2327	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:56.328211
2328	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:56.333309
2329	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:56.389999
2330	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:56.394494
2331	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:56.446257
2332	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:56.451431
2333	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:56.5077
2334	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:56.513036
2335	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:56.565456
2336	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:56.581628
2337	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:56.653051
2338	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:56.658534
2339	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:56.725157
2340	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:56.731783
2341	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:56.800552
2342	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:56.806166
2343	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:56.877539
2344	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:56.884423
2345	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:56.95269
2346	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:56.958212
2347	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:57.035456
2348	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:57.04004
2349	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:57.070834
2350	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:57.074913
2351	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:57.108681
2352	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:57.11261
2353	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:57.143099
2354	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:57.14672
2355	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:57.177398
2356	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:57.181973
2357	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:57.243388
2358	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:57.248497
2359	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:57.300144
2360	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:57.305183
2361	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:57.362339
2362	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:57.367533
2363	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:57.419448
2364	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:57.424461
2365	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:57.483376
2366	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:57.489098
2367	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:57.555441
2368	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:57.561341
2369	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:57.626479
2370	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:57.632704
2371	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:57.697713
2372	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:57.704047
2373	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:57.772487
2374	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:57.780783
2375	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:57.851625
2376	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:57.857137
2377	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:57.921319
2378	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:57.926591
2379	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:57.991715
2380	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:57.99965
2381	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:58.066195
2382	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:58.071971
2383	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:58.13696
2384	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:58.142534
2385	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:58.208159
2386	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:58.213843
2387	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:58.279313
2388	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:58.284973
2389	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:58.350183
2390	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:58.356623
2391	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:58.421408
2392	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:58.554376
2393	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:58.61916
2394	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:58.6291
2395	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:58.69403
2396	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:58.699738
2397	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:58.764282
2398	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:58.769788
2399	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:58.839487
2400	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:58.845077
2401	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:58.910233
2402	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:58.917144
2403	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:58.982723
2404	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:58.988465
2405	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:59.053838
2406	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:59.059625
2407	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:59.124451
2408	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:59.129992
2409	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:59.195702
2410	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:59.202257
2411	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:59.281336
2412	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:59.285339
2413	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:59.349094
2414	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:59.354541
2415	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:59.419849
2416	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:59.425835
2417	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:59.49092
2418	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:59.496955
2419	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:59.561616
2420	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:59.567361
2421	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:59.632483
2422	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:59.638188
2423	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:59.704437
2424	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:59.710157
2425	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:59.775058
2426	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:59.780682
2427	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:59.845555
2428	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:59.851214
2429	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:59.917299
2430	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:51:59.926902
2431	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:51:59.997307
2432	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:00.003094
2433	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:00.067903
2434	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:00.073914
2435	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:00.138524
2436	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:00.144219
2437	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:00.219979
2438	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:00.225879
2439	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:00.306502
2440	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:00.312069
2441	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:00.377088
2442	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:00.382891
2443	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:00.447599
2444	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:00.492306
2445	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:00.578323
2446	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:00.584152
2447	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:00.655506
2448	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:00.661487
2449	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:00.733371
2450	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:00.739198
2451	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:00.8049
2452	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:00.811875
2453	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:00.878056
2454	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:00.883868
2455	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:00.955509
2456	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:00.961688
2457	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:01.029825
2458	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:01.035573
2459	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:01.107218
2460	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:01.113289
2461	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:01.186703
2462	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:01.192459
2463	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:01.263642
2464	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:01.26955
2465	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:01.340648
2466	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:01.346326
2467	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:01.415241
2468	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:01.421497
2469	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:01.487183
2470	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:01.492703
2471	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:01.565927
2472	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:01.571694
2473	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:01.637027
2474	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:01.642615
2475	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:01.712712
2476	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:01.718608
2477	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:01.789837
2478	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:01.795502
2479	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:01.866035
2480	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:01.872036
2481	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:01.944681
2482	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:01.951066
2483	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.044847
2484	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.065801
2485	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.113656
2486	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.118593
2487	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.159144
2488	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.16463
2489	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.199235
2490	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.20719
2491	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.238062
2492	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.242092
2493	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.27303
2494	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.277129
2495	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.308664
2496	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.31292
2497	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.343487
2498	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.347461
2499	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.378107
2500	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.382188
2501	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.415676
2502	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.419837
2503	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.450395
2504	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.454247
2505	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.484829
2506	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.489019
2507	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.522508
2508	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.526833
2509	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.557444
2510	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.56129
2511	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.592663
2512	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.597359
2513	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.629093
2514	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.633371
2515	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.666445
2516	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.670696
2517	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.701513
2518	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.705607
2519	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.743526
2520	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.74891
2521	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.820112
2522	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.825685
2523	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.896816
2524	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.90257
2525	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:02.969839
2526	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:02.976342
2527	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:03.048719
2528	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:03.054548
2529	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:03.12494
2530	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:03.131274
2531	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:03.196395
2532	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:03.20203
2533	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:03.272422
2534	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:03.27801
2535	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:03.349645
2536	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:03.357354
2537	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:03.427892
2538	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:03.43341
2539	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:03.504121
2540	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:03.509842
2541	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:03.574392
2542	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:03.579635
2543	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:03.650655
2544	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:03.656379
2545	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:03.723932
2546	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:03.730296
2547	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:03.795373
2548	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:03.80097
2549	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:03.87123
2550	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:03.876981
2551	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:03.947448
2552	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:03.953022
2553	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.025601
2554	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.031267
2555	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.102359
2556	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.107941
2557	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.196842
2558	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.201575
2559	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.26894
2560	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.273795
2561	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.3158
2562	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.321099
2563	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.358883
2564	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.363186
2565	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.393937
2566	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.398061
2567	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.428256
2568	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.432012
2569	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.465566
2570	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.473061
2571	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.50352
2572	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.507745
2573	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.538304
2574	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.542043
2575	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.575509
2576	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.579634
2577	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.610836
2578	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.61513
2579	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.646054
2580	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.650118
2581	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.680803
2582	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.685255
2583	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.716946
2584	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.721214
2585	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.752141
2586	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.75628
2587	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.787057
2588	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.791105
2589	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.825041
2590	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.830161
2591	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.861254
2592	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.865319
2593	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.895939
2594	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.899979
2595	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.932906
2596	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.937128
2597	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:04.976955
2598	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:04.982071
2599	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:05.049289
2600	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:05.055855
2601	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:05.120892
2602	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:05.126499
2603	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:05.197491
2604	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:05.202992
2605	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:05.26933
2606	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:05.274904
2607	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:05.339568
2608	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:05.345622
2609	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:05.409948
2610	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:05.415992
2611	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:05.480504
2612	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:05.486028
2613	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:05.550922
2614	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:05.556806
2615	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:05.622909
2616	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:05.628725
2617	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:05.694801
2618	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:05.700445
2619	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:05.764801
2620	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:05.771341
2621	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:05.837732
2622	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:05.843334
2623	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:05.908588
2624	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:05.914171
2625	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:05.979169
2626	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:05.984694
2627	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:06.05008
2628	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:06.055667
2629	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:06.120783
2630	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:06.12653
2631	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:06.206663
2632	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:06.211409
2633	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:06.241619
2634	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:06.244496
2635	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:06.27502
2636	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:06.279246
2637	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:06.310481
2638	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:06.31347
2639	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:06.37617
2640	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:06.382362
2641	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:06.450365
2642	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:06.457399
2643	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:06.538595
2644	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:06.541918
2645	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:06.571842
2646	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:06.574977
2647	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:06.625347
2648	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:06.630332
2649	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:06.681936
2650	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:06.686742
2651	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:06.750962
2652	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:06.756899
2653	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:06.822425
2654	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:06.828408
2655	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:06.897094
2656	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:06.903126
2657	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:06.968848
2658	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:06.974973
2659	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:07.041637
2660	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:07.047526
2661	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:07.114537
2662	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:07.121835
2663	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:07.187827
2664	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:07.193716
2665	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:07.268681
2666	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:07.27446
2667	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:07.341843
2668	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:07.347837
2669	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:07.414113
2670	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:07.420076
2671	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:07.486244
2672	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:07.492113
2673	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:07.557147
2674	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:07.562944
2675	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:07.628835
2676	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:07.634476
2677	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:07.700209
2678	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:07.706191
2679	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:07.771613
2680	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:07.779269
2681	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:07.845054
2682	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:07.850802
2683	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:07.916818
2684	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:07.922681
2685	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:07.988835
2686	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:07.994908
2687	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:08.063278
2688	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:08.069294
2689	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:08.137466
2690	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:08.143182
2691	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:08.20866
2692	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:08.214713
2693	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:08.28185
2694	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:08.287734
2695	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:08.353635
2696	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:08.359523
2697	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:08.425558
2698	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:08.431515
2699	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:08.497427
2700	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:08.503315
2701	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:08.570841
2702	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:08.576678
2703	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:08.641944
2704	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:08.648553
2705	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:08.722844
2706	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:08.729458
2707	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:08.794217
2708	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:08.800173
2709	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:08.865972
2710	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:08.871802
2711	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:08.937163
2712	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:08.942938
2713	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:09.007833
2714	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:09.01395
2715	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:09.079809
2716	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:09.086033
2717	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:09.151668
2718	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:09.157621
2719	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:09.238809
2720	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:09.242497
2721	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:09.277026
2722	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:09.280276
2723	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:09.310552
2724	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:09.313783
2725	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:09.343506
2726	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:09.346264
2727	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:09.410349
2728	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:09.41648
2729	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:09.482362
2730	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:09.488316
2731	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:09.553944
2732	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:09.559714
2733	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:09.625843
2734	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:09.631919
2735	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:09.697805
2736	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:09.703736
2737	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:09.770536
2738	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:09.776624
2739	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:09.842046
2740	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:09.848294
2741	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:09.914079
2742	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:09.920468
2743	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:09.986832
2744	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:09.992722
2745	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:10.058592
2746	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:10.064554
2747	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:10.130485
2748	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:10.136357
2749	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:10.20243
2750	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:10.208415
2751	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:10.291171
2752	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:10.297667
2753	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:10.36299
2754	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:10.368722
2755	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:10.433547
2756	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:10.438925
2757	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:10.504224
2758	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:10.510423
2759	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:10.576554
2760	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:10.582019
2761	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:10.648
2762	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:10.65437
2763	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:10.719931
2764	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:10.726498
2765	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:10.796638
2766	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:10.802472
2767	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:10.888971
2768	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:10.895043
2769	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:10.926071
2770	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:10.92894
2771	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:10.958186
2772	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:10.961267
2773	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:10.993228
2774	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:10.997104
2775	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:11.030018
2776	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:11.034041
2777	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:11.098388
2778	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:11.103789
2779	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:11.17499
2780	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:11.180479
2781	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:11.251656
2782	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:11.25741
2783	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:11.324177
2784	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:11.329741
2785	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:11.400642
2786	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:11.406206
2787	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:11.478934
2788	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:11.484925
2789	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:11.556631
2790	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:11.5622
2791	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:11.633185
2792	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:11.638879
2793	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:11.704391
2794	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:11.71023
2795	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:11.780104
2796	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:11.785667
2797	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:11.85674
2798	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:11.86235
2799	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:11.928221
2800	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:11.934005
2801	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:12.011309
2802	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:12.017796
2803	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:12.103372
2804	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:12.109297
2805	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:52:12.140326
2806	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:52:12.144094
2807	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:07.67083
2808	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:07.678149
2809	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:07.755603
2810	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:07.759452
2811	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:07.790786
2812	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:07.794412
2813	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:07.826675
2814	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:07.832865
2815	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:07.901346
2816	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:07.906537
2817	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:07.990885
2818	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:07.996809
2819	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:08.050798
2820	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:08.055414
2821	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:08.112806
2822	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:08.117835
2823	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:08.201717
2824	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:08.208882
2825	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:08.280411
2826	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:08.28693
2827	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:08.357375
2828	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:08.363416
2829	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:08.438565
2830	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:08.445582
2831	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:08.518918
2832	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:08.524036
2833	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:08.554533
2834	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:08.55766
2835	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:08.58785
2836	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:08.591351
2837	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:08.661824
2838	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:08.668028
2839	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:08.737599
2840	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:08.747343
2841	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:08.817951
2842	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:08.823832
2843	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:08.892326
2844	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:08.900975
2845	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:08.973356
2846	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:08.979773
2847	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:09.052187
2848	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:09.058327
2849	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:09.129023
2850	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:09.136221
2851	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:09.228886
2852	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:09.232378
2853	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:09.262775
2854	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:09.266132
2855	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:09.346282
2856	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:09.349884
2857	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:09.416299
2858	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:09.422282
2859	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:09.49118
2860	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:09.497299
2861	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:09.56643
2862	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:09.575934
2863	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:09.656969
2864	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:09.663056
2865	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:09.743854
2866	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:09.748958
2867	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:09.814825
2868	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:09.81984
2869	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:09.894216
2870	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:09.900328
2871	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:09.983443
2872	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:09.990177
2873	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:10.064333
2874	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:10.070804
2875	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:10.140996
2876	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:10.147444
2877	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:10.234335
2878	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:10.238199
2879	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:10.280818
2880	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:10.284574
2881	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:10.330217
2882	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:10.334591
2883	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:10.364452
2884	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:10.367534
2885	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:10.417945
2886	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:10.422494
2887	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:10.474633
2888	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:10.479473
2889	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:10.531355
2890	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:10.536464
2891	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:10.605006
2892	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:10.611186
2893	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:10.679026
2894	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:10.684916
2895	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:10.751945
2896	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:10.759986
2897	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:10.831664
2898	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:10.840479
2899	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:10.907164
2900	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:10.913176
2901	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:10.979613
2902	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:10.985588
2903	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:11.052843
2904	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:11.058693
2905	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:11.126133
2906	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:11.132221
2907	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:11.205229
2908	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:11.211113
2909	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:11.299882
2910	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:11.303664
2911	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:11.358134
2912	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:11.363518
2913	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:11.446784
2914	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:11.451718
2915	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:11.532074
2916	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:11.538336
2917	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:11.58169
2918	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:11.587118
2919	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:11.633138
2920	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:11.639124
2921	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:11.680297
2922	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:11.683785
2923	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:11.731014
2924	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:11.738835
2925	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:11.790882
2926	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:11.794882
2927	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:11.840007
2928	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:11.843656
2929	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:11.881257
2930	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:11.88584
2931	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:11.922231
2932	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:11.925536
2933	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:11.961296
2934	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:11.96471
2935	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:11.999719
2936	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.003098
2937	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.037335
2938	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.040535
2939	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.075198
2940	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.078914
2941	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.127536
2942	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.131493
2943	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.165235
2944	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.168526
2945	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.203164
2946	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.207931
2947	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.249263
2948	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.252877
2949	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.289869
2950	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.293109
2951	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.339488
2952	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.345472
2953	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.392292
2954	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.396093
2955	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.437608
2956	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.440573
2957	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.473105
2958	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.477106
2959	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.508605
2960	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.513022
2961	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.54762
2962	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.551808
2963	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.583906
2964	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.587714
2965	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.621394
2966	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.625358
2967	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.660894
2968	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.664934
2969	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.702004
2970	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.705932
2971	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.74039
2972	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.744353
2973	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.778881
2974	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.784298
2975	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.818785
2976	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.822824
2977	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.857176
2978	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.861144
2979	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.896248
2980	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.900243
2981	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.934615
2982	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.938619
2983	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:12.972807
2984	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:12.976835
2985	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.011623
2986	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.01561
2987	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.049835
2988	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.053824
2989	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.087909
2990	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.091918
2991	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.126825
2992	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.131018
2993	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.164214
2994	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.168476
2995	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.20026
2996	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.204398
2997	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.236038
2998	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.239981
2999	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.272974
3000	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.277
3001	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.311206
3002	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.315221
3003	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.349722
3004	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.35369
3005	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.388846
3006	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.392963
3007	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.427155
3008	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.431234
3009	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.465338
3010	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.469325
3011	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.502929
3012	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.50682
3013	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.54106
3014	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.544995
3015	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.578814
3016	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.582927
3017	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.617854
3018	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.621833
3019	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.65791
3020	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.661965
3021	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.696947
3022	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.701039
3023	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.734716
3024	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.73868
3025	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.77288
3026	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.777152
3027	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.809181
3028	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.813405
3029	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.858445
3030	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.863182
3031	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.909375
3032	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.913839
3033	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:13.959039
3034	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:13.96357
3035	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.00141
3036	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.00544
3037	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.039415
3038	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.0434
3039	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.081578
3040	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.161399
3041	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.195059
3042	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.198675
3043	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.230666
3044	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.233546
3045	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.267001
3046	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.270061
3047	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.302626
3048	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.306559
3049	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.340311
3050	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.344229
3051	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.378141
3052	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.382068
3053	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.416828
3054	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.421001
3055	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.454728
3056	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.458713
3057	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.492808
3058	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.496809
3059	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.530794
3060	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.534883
3061	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.568218
3062	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.572445
3063	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.605736
3064	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.609999
3065	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.641287
3066	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.645305
3067	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.678279
3068	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.682237
3069	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.716168
3070	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.720085
3071	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.754142
3072	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.758136
3073	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.791813
3074	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.795782
3075	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.830433
3076	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.834637
3077	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.868417
3078	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.872781
3079	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.907851
3080	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.911897
3081	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.945743
3082	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.949851
3083	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:14.983615
3084	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:14.987528
3085	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:15.021591
3086	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:15.025516
3087	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:15.059066
3088	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:15.063074
3089	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:15.098614
3090	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:15.102726
3091	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:15.136163
3092	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:15.140523
3093	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:15.18368
3094	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:15.188997
3095	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:15.254811
3096	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:15.261668
3097	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:15.327038
3098	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:15.332744
3099	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:15.397678
3100	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:15.403528
3101	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:15.468332
3102	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:15.474684
3103	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:15.540524
3104	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:15.546273
3105	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:15.613721
3106	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:15.621112
3107	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:15.6897
3108	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:15.698322
3109	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:15.763314
3110	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:15.769189
3111	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:15.834128
3112	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:15.840633
3113	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:15.906292
3114	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:15.91186
3115	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:15.977666
3116	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:15.983785
3117	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:16.048709
3118	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:16.054883
3119	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:16.126672
3120	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:16.134247
3121	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:16.279366
3122	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:16.284636
3123	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:16.352597
3124	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:16.358429
3125	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:16.425214
3126	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:16.431086
3127	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:16.497693
3128	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:16.504361
3129	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:16.570994
3130	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:16.576713
3131	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:16.652092
3132	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:16.684894
3133	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:16.769421
3134	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:16.776073
3135	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:16.842796
3136	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:16.848634
3137	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:16.91434
3138	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:16.920154
3139	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:16.985587
3140	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:16.99125
3141	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:17.056168
3142	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:17.061918
3143	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:17.128136
3144	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:17.133716
3145	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:17.199878
3146	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:17.208085
3147	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:17.272864
3148	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:17.279186
3149	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:17.354202
3150	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:17.360178
3151	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:17.438429
3152	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:17.443194
3153	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:17.476817
3154	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:17.481373
3155	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:17.515507
3156	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:17.520127
3157	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:17.598915
3158	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:17.603197
3159	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:17.637243
3160	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:17.641314
3161	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:17.675328
3162	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:17.679266
3163	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:17.713359
3164	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:17.717309
3165	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:17.748517
3166	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:17.752901
3167	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:17.78481
3168	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:17.788817
3169	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:17.822546
3170	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:17.826454
3171	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:17.860066
3172	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:17.86416
3173	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:17.898575
3174	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:17.902793
3175	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:17.937468
3176	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:17.941434
3177	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:17.975305
3178	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:17.979122
3179	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:18.012638
3180	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:18.017589
3181	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:18.094721
3182	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:18.099205
3183	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:18.14565
3184	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:18.150244
3185	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:18.197538
3186	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:18.202157
3187	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:18.247562
3188	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:18.252807
3189	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:18.288007
3190	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:18.291996
3191	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:18.323252
3192	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:18.328718
3193	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:18.380893
3194	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:18.385728
3195	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:18.437025
3196	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:18.442156
3197	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:18.494036
3198	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:18.499442
3199	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:18.552528
3200	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:18.558682
3201	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:18.613282
3202	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:18.619522
3203	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:18.673174
3204	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:18.678487
3205	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:18.731726
3206	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:18.736552
3207	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:18.787896
3208	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:18.793099
3209	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:18.844463
3210	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:18.849227
3211	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:18.900227
3212	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:18.906288
3213	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:18.959584
3214	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:18.965115
3215	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:19.025605
3216	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:19.030784
3217	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:19.092943
3218	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:19.098423
3219	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:19.155672
3220	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:19.160804
3221	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:19.288799
3222	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:19.351844
3223	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:19.418096
3224	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:19.424013
3225	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:19.489445
3226	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:19.495519
3227	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:19.56116
3228	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:19.567598
3229	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:19.633666
3230	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:19.63964
3231	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:19.705602
3232	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:19.711629
3233	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:19.777807
3234	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:19.783662
3235	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:19.851692
3236	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:19.857703
3237	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:19.924515
3238	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:19.930302
3239	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:19.996052
3240	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:20.002025
3241	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:20.067399
3242	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:20.073628
3243	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:20.139316
3244	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:20.145145
3245	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:20.211518
3246	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:20.217323
3247	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:20.283052
3248	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:20.305432
3249	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:20.373552
3250	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:20.379293
3251	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:20.447016
3252	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:20.453124
3253	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:20.519028
3254	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:20.525003
3255	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:20.591684
3256	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:20.598512
3257	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:20.675131
3258	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:20.681247
3259	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:20.759204
3260	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:20.764829
3261	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:20.842368
3262	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:20.847634
3263	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:20.907094
3264	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:20.913058
3265	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:20.966844
3266	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:20.973926
3267	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:21.038919
3268	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:21.044532
3269	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:21.1094
3270	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:21.115782
3271	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:21.181843
3272	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:21.187556
3273	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:21.25271
3274	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:21.258513
3275	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:21.323443
3276	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:21.330177
3277	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:21.396673
3278	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:21.402782
3279	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:21.469484
3280	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:21.478999
3281	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:21.549823
3282	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:21.557377
3283	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:21.61053
3284	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:21.615367
3285	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:21.668007
3286	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:21.674387
3287	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:21.73495
3288	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:21.74045
3289	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:21.836316
3290	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:21.865369
3291	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:21.937158
3292	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:21.975412
3293	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:22.04153
3294	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:22.047203
3295	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:22.128141
3296	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:22.135192
3297	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:22.201456
3298	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:22.207411
3299	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:22.27421
3300	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:22.280198
3301	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:22.345585
3302	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:22.351657
3303	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:22.417701
3304	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:22.423548
3305	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:22.490944
3306	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:22.497056
3307	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:22.565507
3308	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:22.572087
3309	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:22.642567
3310	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:22.64847
3311	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:22.714329
3312	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:22.720086
3313	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:22.785838
3314	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:22.792128
3315	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:22.858482
3316	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:22.864533
3317	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:22.931069
3318	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:22.937269
3319	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:23.003041
3320	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:23.008985
3321	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:23.07499
3322	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:23.080691
3323	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:23.146393
3324	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:23.152035
3325	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:23.217954
3326	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:23.224067
3327	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:23.289373
3328	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:23.296054
3329	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:23.37031
3330	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:23.37608
3331	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:23.447783
3332	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:23.453607
3333	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:23.523936
3334	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:23.530231
3335	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:23.602918
3336	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:23.608992
3337	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:23.680447
3338	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:23.686543
3339	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:23.756187
3340	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:23.762612
3341	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:23.836733
3342	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:23.842447
3343	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:23.908456
3344	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:23.916068
3345	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:23.983823
3346	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:23.989615
3347	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:24.060932
3348	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:24.066657
3349	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:24.131901
3350	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:24.137663
3351	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:24.209377
3352	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:24.215104
3353	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:24.286439
3354	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:24.292129
3355	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:24.363207
3356	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:24.369042
3357	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:24.45416
3358	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:24.458595
3359	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:24.530571
3360	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:24.537804
3361	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:24.629402
3362	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:24.634493
3363	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:24.687269
3364	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:24.692038
3365	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:24.732903
3366	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:24.737719
3367	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:24.773497
3368	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:24.777846
3369	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:24.808832
3370	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:24.81274
3371	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:24.843689
3372	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:24.847993
3373	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:24.883682
3374	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:24.888065
3375	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:24.919243
3376	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:24.924507
3377	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:24.989865
3378	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:24.996008
3379	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:25.060868
3380	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:25.066494
3381	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:25.131435
3382	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:25.137409
3383	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:25.201995
3384	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:25.207628
3385	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:25.272955
3386	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:25.2787
3387	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:25.344198
3388	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:25.350213
3389	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:25.415207
3390	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:25.420867
3391	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:25.485815
3392	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:25.491678
3393	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:25.558146
3394	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:25.56397
3395	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:25.629014
3396	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:25.6347
3397	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:25.699694
3398	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:25.706155
3399	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:25.773074
3400	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:25.778675
3401	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:25.843797
3402	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:25.849557
3403	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:25.914597
3404	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:25.921065
3405	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:25.986932
3406	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:25.992659
3407	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:26.057899
3408	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:26.063812
3409	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:26.130193
3410	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:26.137687
3411	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:26.203698
3412	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:26.209806
3413	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:26.274534
3414	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:26.280505
3415	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:26.345989
3416	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:26.351738
3417	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:26.416598
3418	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:26.422248
3419	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:26.48807
3420	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:26.494012
3421	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:26.559143
3422	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:26.565226
3423	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:26.630487
3424	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:26.636394
3425	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:26.702237
3426	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:26.708099
3427	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:26.773348
3428	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:26.779624
3429	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:26.847027
3430	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:26.853293
3431	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:26.923656
3432	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:26.929189
3433	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:27.004315
3434	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:27.010491
3435	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:27.075637
3436	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:27.081523
3437	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:27.146138
3438	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:27.151575
3439	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:27.216722
3440	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:27.222537
3441	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:27.287359
3442	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:27.293102
3443	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:27.358452
3444	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:27.365232
3445	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:27.430739
3446	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:27.436722
3447	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:27.501736
3448	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:27.507497
3449	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:27.574416
3450	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:27.580261
3451	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:27.645848
3452	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:27.651674
3453	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:27.717301
3454	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:27.723339
3455	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:27.789409
3456	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:27.795277
3457	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:27.862141
3458	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:27.868547
3459	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:27.933944
3460	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:27.939818
3461	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:28.004505
3462	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:28.010147
3463	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:28.075609
3464	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:28.081382
3465	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:28.146994
3466	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:28.152982
3467	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:28.218079
3468	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:28.223961
3469	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:28.289483
3470	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:28.295488
3471	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:28.360126
3472	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:28.365925
3473	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:28.431146
3474	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:28.43729
3475	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:28.502653
3476	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:28.508466
3477	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:28.573723
3478	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:28.579548
3479	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:28.644382
3480	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:28.650184
3481	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:28.715118
3482	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:28.721524
3483	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:28.787151
3484	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:28.792937
3485	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:28.857588
3486	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:28.863171
3487	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:28.928244
3488	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:28.934607
3489	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:28.999377
3490	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:29.005411
3491	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:29.07605
3492	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:29.082372
3493	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:29.15339
3494	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:29.159721
3495	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:29.223964
3496	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:29.229824
3497	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:29.309826
3498	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:29.313822
3499	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:29.343132
3500	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:29.346486
3501	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:29.376245
3502	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:29.380499
3503	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:29.443898
3504	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:29.449461
3505	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:29.513673
3506	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:29.519938
3507	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:29.584614
3508	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:29.590455
3509	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:29.655739
3510	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:29.661698
3511	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:29.726102
3512	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:29.732159
3513	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:29.797329
3514	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:29.803044
3515	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:29.86725
3516	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:29.873205
3517	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:29.936873
3518	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:29.942689
3519	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:30.00713
3520	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:30.013021
3521	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:30.077471
3522	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:30.083175
3523	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:30.147218
3524	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:30.152811
3525	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:30.216889
3526	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:30.222586
3527	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:30.296953
3528	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:30.30279
3529	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:30.367914
3530	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:30.374042
3531	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:30.438363
3532	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:30.4441
3533	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:30.508001
3534	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:30.513939
3535	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:30.578268
3536	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:30.584244
3537	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:30.648843
3538	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:30.654473
3539	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:30.718979
3540	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:30.725036
3541	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:30.795222
3542	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:30.8012
3543	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:30.865065
3544	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:30.871498
3545	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:30.936995
3546	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:30.942742
3547	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:31.007684
3548	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:31.01343
3549	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:31.078321
3550	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:31.084087
3551	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:31.148819
3552	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:31.154682
3553	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:31.224162
3554	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:31.234391
3555	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:31.300687
3556	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:31.306224
3557	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:31.370592
3558	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:31.376497
3559	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:31.440708
3560	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:31.446368
3561	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:31.511039
3562	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:31.516939
3563	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:31.581126
3564	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:31.586922
3565	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:31.651381
3566	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:31.657408
3567	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:31.721827
3568	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:31.727563
3569	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:31.792795
3570	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:31.798684
3571	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:31.866842
3572	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:31.872731
3573	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:31.936861
3574	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:31.942671
3575	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:32.007051
3576	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:32.012669
3577	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:32.092409
3578	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:32.097632
3579	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:32.162062
3580	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:32.168057
3581	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:32.232493
3582	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:32.238209
3583	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:32.30171
3584	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:32.307159
3585	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:32.371474
3586	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:32.377222
3587	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:32.44129
3588	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:32.447367
3589	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:32.511918
3590	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:32.517907
3591	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:32.582076
3592	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:32.588106
3593	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:32.652343
3594	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:32.658157
3595	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:32.722162
3596	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:32.728021
3597	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:32.791914
3598	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:32.797605
3599	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:32.861825
3600	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:32.86753
3601	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:32.931381
3602	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:32.937351
3603	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:33.002103
3604	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:33.007891
3605	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:33.07224
3606	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:33.078145
3607	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:33.141858
3608	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:33.1475
3609	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:33.211785
3610	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:33.217538
3611	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:33.281789
3612	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:33.287521
3613	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:33.352026
3614	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:33.357741
3615	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:33.428505
3616	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:33.43462
3617	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:33.501254
3618	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:33.506813
3619	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:33.571013
3620	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:33.576821
3621	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:33.641284
3622	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:33.647151
3623	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:33.711793
3624	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:33.717505
3625	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:33.781537
3626	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:33.787407
3627	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:33.852131
3628	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:33.857927
3629	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:33.923162
3630	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:33.928961
3631	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:33.993161
3632	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:33.998953
3633	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:34.064517
3634	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:34.070336
3635	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:34.134158
3636	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:34.13994
3637	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:34.204369
3638	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:34.210235
3639	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:34.274819
3640	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:34.28052
3641	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:34.344323
3642	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:34.349917
3643	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:34.413965
3644	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:34.420545
3645	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:34.484388
3646	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:34.489915
3647	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:34.554733
3648	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:34.560734
3649	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:34.625086
3650	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:34.63109
3651	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:34.695812
3652	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:34.701434
3653	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:34.76529
3654	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:34.770891
3655	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:34.834858
3656	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:34.840513
3657	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:34.904698
3658	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:34.910411
3659	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:34.974589
3660	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:34.980559
3661	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:35.044832
3662	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:35.050687
3663	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:35.114982
3664	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:35.120671
3665	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:35.184687
3666	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:35.190372
3667	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:35.254943
3668	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:35.260695
3669	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:35.325139
3670	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:35.330951
3671	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:35.395977
3672	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:35.40178
3673	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:35.481962
3674	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:35.486175
3675	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:35.515622
3676	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:35.518681
3677	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:35.585653
3678	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:35.593002
3679	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:35.659071
3680	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:35.665265
3681	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:35.729057
3682	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:35.73515
3683	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:35.800315
3684	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:35.806808
3685	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:35.870813
3686	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:35.876666
3687	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:35.940227
3688	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:35.946013
3689	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:36.009863
3690	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:36.015512
3691	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:36.079081
3692	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:36.084663
3693	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:36.148517
3694	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:36.154352
3695	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:36.218621
3696	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:36.224948
3697	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:36.289717
3698	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:36.297311
3699	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:36.363213
3700	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:36.369091
3701	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:36.435686
3702	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:36.441576
3703	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:36.506604
3704	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:36.512501
3705	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:36.577007
3706	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:36.583296
3707	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:36.648011
3708	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:36.653629
3709	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:36.717568
3710	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:36.723392
3711	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:36.78733
3712	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:36.793124
3713	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:36.856788
3714	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:36.862357
3715	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:36.92627
3716	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:36.932061
3717	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:36.996895
3718	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:37.002687
3719	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:37.068096
3720	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:37.073994
3721	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:37.138503
3722	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:37.144546
3723	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:37.208828
3724	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:37.214481
3725	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:37.283433
3726	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:37.289209
3727	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:37.353584
3728	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:37.359324
3729	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:37.423694
3730	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:37.429979
3731	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:37.496604
3732	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:37.502486
3733	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:37.568178
3734	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:37.574489
3735	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:37.63965
3736	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:37.64607
3737	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:37.711842
3738	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:37.71828
3739	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:37.790148
3740	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:37.796852
3741	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:37.862848
3742	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:37.868364
3743	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:37.932566
3744	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:37.939364
3745	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:38.003327
3746	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:38.009249
3747	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:38.073159
3748	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:38.078799
3749	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:38.14249
3750	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:38.148073
3751	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:38.212097
3752	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:38.217825
3753	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:38.28217
3754	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:38.288573
3755	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:38.353664
3756	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:38.359462
3757	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:38.424118
3758	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:38.429981
3759	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:38.493985
3760	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:38.499885
3761	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:38.564598
3762	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:38.570813
3763	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:38.635008
3764	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:38.640677
3765	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:38.704984
3766	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:38.710545
3767	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:38.774505
3768	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:38.78042
3769	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:38.844408
3770	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:38.850393
3771	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:38.923176
3772	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:38.928384
3773	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:38.958099
3774	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:38.961581
3775	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:38.991666
3776	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:38.997061
3777	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:39.068585
3778	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:39.076206
3779	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:39.149691
3780	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:39.155639
3781	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:39.220472
3782	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:39.226436
3783	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:39.310647
3784	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:39.31545
3785	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:39.385725
3786	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:39.391266
3787	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:39.455638
3788	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:39.461258
3789	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:39.533925
3790	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:39.539657
3791	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:39.616557
3792	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:39.623055
3793	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:39.688471
3794	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:39.694321
3795	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:39.773738
3796	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:39.77863
3797	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:39.822862
3798	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:39.828938
3799	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:39.876331
3800	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:39.881193
3801	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:39.959508
3802	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:39.965495
3803	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.032367
3804	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.038034
3805	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.105723
3806	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.111815
3807	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.17844
3808	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.184378
3809	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.253851
3810	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.27293
3811	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.30484
3812	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.308738
3813	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.340045
3814	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.344182
3815	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.375214
3816	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.379035
3817	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.410174
3818	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.414341
3819	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.445114
3820	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.448778
3821	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.479721
3822	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.483527
3823	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.515564
3824	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.519525
3825	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.550871
3826	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.555254
3827	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.586793
3828	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.590579
3829	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.621652
3830	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.625632
3831	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.656736
3832	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.660678
3833	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.691347
3834	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.695121
3835	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.725925
3836	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.72972
3837	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.761461
3838	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.766119
3839	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.798977
3840	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.803028
3841	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.833954
3842	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.838725
3843	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.870353
3844	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.874301
3845	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.904976
3846	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.908835
3847	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.940106
3848	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.94386
3849	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:40.974574
3850	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:40.978389
3851	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:41.009187
3852	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:41.013276
3853	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:41.044433
3854	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:41.049276
3855	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:41.101839
3856	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:41.107812
3857	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:41.160743
3858	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:41.16748
3859	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:41.220886
3860	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:41.225997
3861	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:41.278186
3862	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:41.283725
3863	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:41.33683
3864	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:41.341947
3865	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:41.395443
3866	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:41.401018
3867	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:41.46734
3868	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:41.4731
3869	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:41.540304
3870	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:41.546581
3871	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:41.614122
3872	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:41.62043
3873	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:41.686992
3874	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:41.693058
3875	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:41.759734
3876	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:41.766176
3877	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:41.819661
3878	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:41.826331
3879	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:41.895107
3880	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:41.901265
3881	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:41.966838
3882	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:41.972944
3883	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:42.041926
3884	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:42.064451
3885	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:42.136537
3886	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:42.142442
3887	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:42.208302
3888	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:42.214135
3889	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:42.281814
3890	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:42.288351
3891	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:42.353917
3892	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:42.360224
3893	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:42.426701
3894	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:42.432359
3895	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:42.498307
3896	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:42.504168
3897	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:42.571595
3898	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:42.57746
3899	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:42.643418
3900	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:42.651785
3901	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:42.719028
3902	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:42.725301
3903	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:42.813583
3904	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:42.833359
3905	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:42.867577
3906	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:42.870741
3907	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:42.901224
3908	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:42.904427
3909	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:42.933775
3910	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:42.936551
3911	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:42.966676
3912	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:42.969994
3913	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:43.000091
3914	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:43.003606
3915	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:43.03444
3916	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:43.03759
3917	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:43.067497
3918	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:43.070772
3919	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:43.100494
3920	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:43.103472
3921	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:43.133332
3922	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:43.13619
3923	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:43.186651
3924	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:43.191956
3925	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:43.243465
3926	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:43.249416
3927	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:43.308187
3928	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:43.312842
3929	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:43.365434
3930	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:43.36998
3931	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:43.421519
3932	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:43.42619
3933	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:43.47762
3934	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:43.482325
3935	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:43.534384
3936	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:43.539154
3937	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:43.590611
3938	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:43.59556
3939	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:43.648694
3940	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:43.653385
3941	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:43.705495
3942	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:43.710657
3943	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:43.775487
3944	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:43.781028
3945	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:43.846922
3946	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:43.852743
3947	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:43.91928
3948	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:43.924899
3949	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:43.990356
3950	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:43.996173
3951	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:44.061393
3952	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:44.067112
3953	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:44.13355
3954	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:44.139651
3955	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:44.205462
3956	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:44.210297
3957	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:44.290992
3958	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:44.295865
3959	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:44.327824
3960	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:44.332196
3961	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:44.396353
3962	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:44.402704
3963	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:44.467991
3964	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:44.473517
3965	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:44.53807
3966	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:44.543653
3967	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:44.609531
3968	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:44.615168
3969	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:44.680069
3970	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:44.685792
3971	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:44.750818
3972	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:44.757499
3973	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:44.822516
3974	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:44.828214
3975	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:44.894155
3976	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:44.899792
3977	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:44.965097
3978	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:44.970668
3979	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:45.035171
3980	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:45.041043
3981	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:45.106076
3982	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:45.111789
3983	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:45.177976
3984	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:45.183781
3985	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:45.248848
3986	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:45.256297
3987	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:45.321005
3988	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:45.32645
3989	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:45.391218
3990	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:45.396971
3991	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:45.462607
3992	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:45.468216
3993	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:45.532827
3994	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:45.538427
3995	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:45.604098
3996	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:45.609638
3997	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:45.674372
3998	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:45.680058
3999	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:45.744422
4000	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:45.75006
4001	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:45.815227
4002	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:45.82097
4003	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:45.88583
4004	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:45.89169
4005	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:45.956457
4006	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:45.962813
4007	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:46.028292
4008	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:46.033822
4009	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:46.098838
4010	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:46.104952
4011	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:46.18685
4012	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:46.191212
4013	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:46.259453
4014	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:46.269713
4015	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:46.335341
4016	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:46.341443
4017	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:46.412198
4018	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:46.41863
4019	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:46.489664
4020	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:46.495498
4021	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:46.560978
4022	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:46.567151
4023	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:46.633117
4024	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:46.639089
4025	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:46.704345
4026	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:46.710244
4027	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:46.775259
4028	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:46.781317
4029	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:46.84674
4030	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:46.852694
4031	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:46.919126
4032	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:46.925492
4033	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:46.992813
4034	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:46.99857
4035	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:47.06346
4036	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:47.069549
4037	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:47.137073
4038	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:47.14274
4039	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:47.208231
4040	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:47.214136
4041	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:47.280299
4042	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:47.286427
4043	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:47.352414
4044	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:47.357782
4045	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:47.422634
4046	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:47.428742
4047	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:47.494477
4048	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:47.500286
4049	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:47.565223
4050	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:47.572148
4051	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:47.638354
4052	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:47.644011
4053	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:47.709391
4054	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:47.715142
4055	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:47.780215
4056	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:47.786035
4057	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:47.850821
4058	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:47.856735
4059	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:47.924044
4060	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:47.929805
4061	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:47.994689
4062	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:48.000337
4063	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:48.066819
4064	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:48.072515
4065	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:48.143501
4066	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:48.149167
4067	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:48.214107
4068	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:48.220038
4069	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:48.295832
4070	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:48.301677
4071	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:48.372334
4072	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:48.377978
4073	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:48.462009
4074	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:48.466603
4075	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:48.512898
4076	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:48.517443
4077	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:48.565013
4078	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:48.572221
4079	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:48.609436
4080	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:48.612544
4081	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:48.644847
4082	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:48.649136
4083	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:48.680059
4084	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:48.684116
4085	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:48.71491
4086	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:48.7188
4087	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:48.751054
4088	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:48.75534
4089	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:48.786049
4090	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:48.789963
4091	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:48.820503
4092	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:48.82452
4093	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:48.858272
4094	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:48.862577
4095	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:48.893436
4096	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:48.897377
4097	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:48.928603
4098	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:48.932647
4099	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:48.966263
4100	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:48.970567
4101	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.002028
4102	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.006186
4103	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.037263
4104	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.041476
4105	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.072997
4106	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.077287
4107	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.110933
4108	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.115117
4109	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.14598
4110	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.149955
4111	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.185155
4112	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.189313
4113	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.239291
4114	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.243933
4115	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.278039
4116	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.282256
4117	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.313375
4118	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.317959
4119	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.350984
4120	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.355072
4121	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.386165
4122	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.390453
4123	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.421371
4124	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.425307
4125	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.459244
4126	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.463491
4127	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.494854
4128	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.499362
4129	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.5332
4130	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.538379
4131	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.572534
4132	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.577058
4133	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.608513
4134	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.612718
4135	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.64391
4136	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.64804
4137	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.680717
4138	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.685303
4139	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.716876
4140	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.721057
4141	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.752489
4142	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.756799
4143	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.791927
4144	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.796353
4145	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.827596
4146	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.831789
4147	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.864296
4148	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.86853
4149	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.899993
4150	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.904132
4151	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.938121
4152	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.942217
4153	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:49.973193
4154	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:49.977571
4155	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:50.008492
4156	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:50.012479
4157	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:50.045686
4158	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:50.049898
4159	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:50.080983
4160	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:50.085002
4161	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:50.115718
4162	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:50.119722
4163	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:50.150496
4164	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:50.154622
4165	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:50.188252
4166	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:50.19254
4167	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:50.223561
4168	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:50.22748
4169	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:50.274025
4170	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:50.278333
4171	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:50.312044
4172	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:50.316318
4173	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:50.348041
4174	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:50.352372
4175	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:50.386037
4176	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:50.390326
4177	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:50.422335
4178	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:50.426635
4179	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:50.460955
4180	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:50.465264
4181	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:50.496419
4182	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:50.50081
4183	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:50.535385
4184	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:50.539649
4185	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:50.593844
4186	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:50.765488
4187	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:50.812979
4188	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:50.817828
4189	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:50.864484
4190	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:50.869619
4191	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:50.91029
4192	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:50.915073
4193	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:50.949697
4194	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:50.954605
4195	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:51.007171
4196	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:51.013002
4197	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:51.079852
4198	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:51.085723
4199	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:51.152267
4200	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:51.158148
4201	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:51.22482
4202	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:51.230605
4203	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:51.296814
4204	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:51.302797
4205	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:51.368181
4206	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:51.37405
4207	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:51.439269
4208	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:51.445257
4209	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:51.510677
4210	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:51.516824
4211	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:51.5822
4212	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:51.588053
4213	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:51.653216
4214	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:51.659148
4215	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:51.724301
4216	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:51.729985
4217	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:51.795555
4218	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:51.801257
4219	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:51.866334
4220	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:51.873512
4221	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:51.939435
4222	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:51.945192
4223	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:52.010503
4224	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:52.016238
4225	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:52.100882
4226	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:52.102689
4227	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:52.168301
4228	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:52.17402
4229	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:52.238912
4230	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:52.244534
4231	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:52.314426
4232	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:52.320118
4233	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:52.384998
4234	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:52.390594
4235	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:52.455436
4236	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:52.461965
4237	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:52.527447
4238	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:52.533323
4239	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:52.598337
4240	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:52.604158
4241	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:52.669151
4242	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:52.674799
4243	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:52.739409
4244	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:52.745955
4245	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:52.812022
4246	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:52.817816
4247	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:52.882866
4248	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:52.889075
4249	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:52.954136
4250	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:52.960592
4251	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:53.026938
4252	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:53.093162
4253	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:53.16685
4254	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:53.172586
4255	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:53.237474
4256	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:53.243132
4257	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:53.309186
4258	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:53.314998
4259	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:53.380035
4260	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:53.385917
4261	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:53.450396
4262	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:53.456031
4263	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:53.521219
4264	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:53.527324
4265	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:53.592836
4266	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:53.598634
4267	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:53.664924
4268	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:53.670619
4269	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:53.736944
4270	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:53.742586
4271	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:53.808226
4272	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:53.814111
4273	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:53.879988
4274	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:53.887685
4275	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:53.95397
4276	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:53.95982
4277	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:54.024905
4278	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:54.030584
4279	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:54.096047
4280	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:54.10191
4281	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:54.166946
4282	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:54.172745
4283	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:54.238144
4284	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:54.244055
4285	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:54.309431
4286	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:54.315402
4287	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:54.380992
4288	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:54.386807
4289	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:54.451607
4290	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:54.457571
4291	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:54.523066
4292	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:54.528884
4293	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:54.594261
4294	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:54.600372
4295	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:54.665473
4296	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:54.671227
4297	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:54.736825
4298	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:54.742682
4299	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:54.807525
4300	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:54.813379
4301	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:54.878426
4302	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:54.884345
4303	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:54.949651
4304	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:54.955435
4305	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:55.02168
4306	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:55.02755
4307	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:55.102954
4308	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:55.108809
4309	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:55.17437
4310	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:55.180453
4311	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:55.247342
4312	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:55.25531
4313	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:55.341304
4314	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:55.345649
4315	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:55.377273
4316	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:55.380381
4317	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:55.410539
4318	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:55.413899
4319	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:55.48416
4320	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:55.488182
4321	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:55.518949
4322	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:55.522597
4323	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:55.552728
4324	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:55.556949
4325	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:55.589801
4326	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:55.594208
4327	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:55.625568
4328	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:55.63056
4329	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:55.701166
4330	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:55.706803
4331	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:55.772604
4332	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:55.778176
4333	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:55.849488
4334	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:55.855507
4335	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:55.928311
4336	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:55.935019
4337	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:56.005663
4338	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:56.011395
4339	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:56.076285
4340	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:56.082051
4341	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:56.146636
4342	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:56.15238
4343	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:56.21743
4344	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:56.223321
4345	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:56.288353
4346	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:56.294516
4347	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:56.359169
4348	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:56.364917
4349	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:56.445825
4350	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:56.449714
4351	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:56.479395
4352	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:56.48245
4353	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:56.51236
4354	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:56.515617
4355	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:56.56605
4356	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:56.571341
4357	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:56.623096
4358	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:56.627873
4359	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:56.685008
4360	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:56.690352
4361	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:56.742066
4362	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:56.746775
4363	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:56.803283
4364	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:56.808706
4365	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:56.860179
4366	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:56.865199
4367	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:56.921397
4368	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:56.926793
4369	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:56.981074
4370	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:56.986524
4371	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:57.042936
4372	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:57.048249
4373	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:57.104047
4374	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:57.109388
4375	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:57.165607
4376	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:57.171093
4377	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:57.222908
4378	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:57.228141
4379	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:57.285707
4380	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:57.291721
4381	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:57.372524
4382	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:57.378469
4383	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:57.432792
4384	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:57.437468
4385	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:57.481275
4386	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:57.487108
4387	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:57.545006
4388	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:57.550332
4389	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:57.604975
4390	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:57.613866
4391	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:57.681823
4392	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:57.687445
4393	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:57.758407
4394	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:57.764238
4395	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:57.829021
4396	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:57.834714
4397	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:57.904916
4398	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:57.910713
4399	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:57.981669
4400	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:57.98727
4401	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:58.052439
4402	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:58.05868
4403	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:58.132702
4404	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:58.138473
4405	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:58.206834
4406	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:58.213319
4407	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:58.278188
4408	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:58.283957
4409	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:58.357735
4410	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:58.363995
4411	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:58.429136
4412	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:58.434604
4413	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:58.505453
4414	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:58.511207
4415	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:58.587445
4416	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:58.593467
4417	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:58.660825
4418	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:58.669277
4419	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:58.740013
4420	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:58.745866
4421	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:58.816158
4422	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:58.821964
4423	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:58.886951
4424	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:58.892738
4425	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:58.964938
4426	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:58.971053
4427	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:59.03632
4428	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:59.042922
4429	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:59.109468
4430	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:59.115565
4431	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:59.186591
4432	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:59.192394
4433	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:59.277668
4434	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:59.282328
4435	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:59.352451
4436	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:59.359217
4437	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:59.429616
4438	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:59.435367
4439	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:59.523958
4440	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:59.528711
4441	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:59.571891
4442	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:59.576536
4443	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:59.622938
4444	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:59.628017
4445	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:59.689901
4446	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:59.695694
4447	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:59.748933
4448	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:59.754205
4449	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:59.825857
4450	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:59.831457
4451	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:59.89583
4452	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:59.901725
4453	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:54:59.970686
4454	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:54:59.976859
4455	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:00.047839
4456	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:00.05353
4457	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:00.117807
4458	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:00.123293
4459	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:00.196484
4460	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:00.202284
4461	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:00.28909
4462	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:00.294693
4463	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:00.362345
4464	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:00.368169
4465	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:00.438619
4466	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:00.44442
4467	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:00.513997
4468	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:00.520212
4469	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:00.590326
4470	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:00.596101
4471	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:00.666909
4472	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:00.672546
4473	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:00.736827
4474	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:00.742868
4475	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:00.812159
4476	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:00.817656
4477	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:00.888426
4478	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:00.894315
4479	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:00.961845
4480	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:00.967308
4481	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:01.037506
4482	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:01.043094
4483	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:01.110839
4484	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:01.117036
4485	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:01.181579
4486	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:01.187323
4487	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:01.25793
4488	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:01.264649
4489	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:01.330103
4490	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:01.336037
4491	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:01.406971
4492	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:01.412783
4493	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:01.485164
4494	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:01.490885
4495	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:01.566019
4496	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:01.571799
4497	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:01.653962
4498	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:01.658873
4499	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:01.705788
4500	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:01.710328
4501	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:01.756138
4502	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:01.761153
4503	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:01.801375
4504	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:01.806051
4505	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:01.837887
4506	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:01.842126
4507	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:01.873334
4508	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:01.877477
4509	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:01.909901
4510	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:01.912937
4511	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:01.945457
4512	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:01.949689
4513	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:01.980477
4514	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:01.984883
4515	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:02.033147
4516	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:02.034101
4517	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:02.067226
4518	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:02.071473
4519	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:02.102171
4520	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:02.106127
4521	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:02.136962
4522	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:02.141129
4523	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:02.175203
4524	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:02.179587
4525	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:02.210136
4526	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:02.21435
4527	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:02.244815
4528	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:02.248788
4529	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:02.282247
4530	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:02.286413
4531	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:02.316978
4532	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:02.320988
4533	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:02.3513
4534	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:02.355202
4535	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:02.402061
4536	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:02.408993
4537	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:02.478839
4538	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:02.484579
4539	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:02.55564
4540	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:02.561474
4541	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:02.629414
4542	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:02.63512
4543	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:02.706113
4544	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:02.711802
4545	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:02.780836
4546	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:02.787248
4547	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:02.853527
4548	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:02.859114
4549	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:02.929927
4550	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:02.93565
4551	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:03.008965
4552	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:03.015409
4553	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:03.083931
4554	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:03.089683
4555	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:03.160837
4556	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:03.166725
4557	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:03.231527
4558	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:03.237126
4559	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:03.307134
4560	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:03.312817
4561	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:03.379278
4562	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:03.38787
4563	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:03.452393
4564	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:03.45806
4565	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:03.528706
4566	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:03.534184
4567	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:03.611469
4568	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:03.618082
4569	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:03.684835
4570	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:03.690426
4571	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:03.761163
4572	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:03.768099
4573	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:03.859007
4574	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:03.862944
4575	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:03.912291
4576	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:03.916258
4577	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:03.946548
4578	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:03.95057
4579	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:04.009645
4580	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:04.015512
4581	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:04.080581
4582	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:04.086387
4583	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:04.151723
4584	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:04.157556
4585	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:04.222226
4586	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:04.228298
4587	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:04.293958
4588	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:04.299984
4589	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:04.364039
4590	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:04.370148
4591	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:04.4343
4592	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:04.439993
4593	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:04.504221
4594	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:04.510315
4595	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:04.575174
4596	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:04.581309
4597	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:04.645911
4598	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:04.652122
4599	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:04.716214
4600	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:04.722313
4601	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:04.786437
4602	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:04.792302
4603	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:04.856525
4604	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:04.862448
4605	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:04.926273
4606	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:04.932094
4607	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:04.996935
4608	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:05.002847
4609	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:05.069246
4610	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:05.075401
4611	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:05.141952
4612	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:05.1481
4613	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:05.215479
4614	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:05.221554
4615	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:05.287508
4616	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:05.293635
4617	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:05.359788
4618	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:05.365811
4619	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:05.432087
4620	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:05.438431
4621	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:05.505216
4622	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:05.511984
4623	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:05.580575
4624	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:05.586978
4625	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:05.653421
4626	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:05.659684
4627	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:05.726193
4628	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:05.732242
4629	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:05.799432
4630	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:05.805458
4631	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:05.872736
4632	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:05.878599
4633	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:05.942567
4634	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:05.948595
4635	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:06.018057
4636	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:06.025082
4637	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:06.092843
4638	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:06.098968
4639	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:06.167099
4640	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:06.172821
4641	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:06.236637
4642	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:06.242192
4643	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:06.306677
4644	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:06.31259
4645	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:06.376521
4646	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:06.382432
4647	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:06.446835
4648	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:06.452568
4649	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:06.517034
4650	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:06.52266
4651	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:06.587338
4652	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:06.593241
4653	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:06.658713
4654	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:06.664385
4655	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:06.73
4656	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:06.736052
4657	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:06.801267
4658	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:06.80731
4659	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:06.871558
4660	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:06.877336
4661	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:06.941578
4662	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:06.947642
4663	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:07.013124
4664	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:07.018879
4665	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:07.087701
4666	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:07.09352
4667	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:07.158527
4668	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:07.164092
4669	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:07.228871
4670	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:07.234649
4671	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:07.303521
4672	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:07.309245
4673	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:07.374707
4674	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:07.380747
4675	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:07.461071
4676	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:07.466815
4677	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:07.532488
4678	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:07.538309
4679	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:07.602847
4680	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:07.608642
4681	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:07.672944
4682	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:07.67879
4683	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:07.743078
4684	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:07.7489
4685	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:07.813342
4686	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:07.819092
4687	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:07.884051
4688	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:07.889791
4689	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:07.954635
4690	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:07.960371
4691	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:08.025671
4692	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:08.031419
4693	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:08.096645
4694	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:08.102499
4695	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:08.167498
4696	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:08.173349
4697	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:08.238044
4698	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:08.243546
4699	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:08.313647
4700	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:08.319211
4701	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:08.383614
4702	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:08.389601
4703	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:08.454318
4704	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:08.460005
4705	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:08.524848
4706	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:08.532415
4707	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:08.597507
4708	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:08.603465
4709	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:08.668271
4710	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:08.674133
4711	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:08.738052
4712	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:08.743656
4713	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:08.808596
4714	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:08.814436
4715	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:08.879065
4716	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:08.884655
4717	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:08.948955
4718	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:09.085138
4719	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:09.114722
4720	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:09.118125
4721	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:09.18188
4722	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:09.204278
4723	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:09.268921
4724	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:09.274726
4725	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:09.338994
4726	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:09.344731
4727	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:09.409061
4728	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:09.414891
4729	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:09.479408
4730	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:09.485136
4731	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:09.550442
4732	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:09.556179
4733	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:09.620848
4734	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:09.626797
4735	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:09.691679
4736	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:09.697501
4737	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:09.761655
4738	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:09.767613
4739	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:09.832302
4740	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:09.837963
4741	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:09.902788
4742	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:09.908531
4743	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:09.972986
4744	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:09.978825
4745	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:10.043369
4746	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:10.049093
4747	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:10.113482
4748	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:10.119227
4749	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:10.184295
4750	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:10.190068
4751	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:10.270683
4752	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:10.27448
4753	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:10.338735
4754	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:10.344599
4755	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:10.410237
4756	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:10.417825
4757	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:10.487266
4758	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:10.493062
4759	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:10.557846
4760	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:10.56531
4761	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:10.629841
4762	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:10.635598
4763	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:10.699867
4764	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:10.705804
4765	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:10.770562
4766	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:10.776249
4767	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:10.929523
4768	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:10.945029
4769	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:11.009914
4770	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:11.015564
4771	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:11.081682
4772	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:11.087484
4773	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:11.152122
4774	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:11.15809
4775	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:11.223221
4776	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:11.229145
4777	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:11.295744
4778	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:11.301999
4779	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:11.366726
4780	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:11.372637
4781	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:11.43754
4782	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:11.443594
4783	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:11.507982
4784	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:11.513472
4785	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:11.578074
4786	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:11.583807
4787	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:11.648605
4788	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:11.654723
4789	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:11.719446
4790	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:11.725393
4791	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:11.789971
4792	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:11.795809
4793	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:11.860218
4794	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:11.866155
4795	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:11.931045
4796	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:11.936902
4797	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:12.020774
4798	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:12.022774
4799	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:12.086008
4800	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:12.091588
4801	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:12.156171
4802	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:12.162264
4803	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:12.226824
4804	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:12.232455
4805	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:12.298372
4806	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:12.304511
4807	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:12.37172
4808	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:12.377587
4809	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:12.443283
4810	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:12.449218
4811	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:12.513317
4812	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:12.519183
4813	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:12.588476
4814	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:12.594445
4815	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:12.663288
4816	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:12.668888
4817	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:12.733517
4818	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:12.739207
4819	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:12.803911
4820	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:12.809646
4821	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:12.873829
4822	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:12.879595
4823	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:12.943436
4824	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:12.950319
4825	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:13.015246
4826	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:13.021248
4827	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:13.085865
4828	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:13.091495
4829	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:13.155596
4830	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:13.161442
4831	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:13.226096
4832	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:13.232016
4833	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:13.301853
4834	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:13.307597
4835	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:13.371793
4836	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:13.377443
4837	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:13.441742
4838	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:13.447711
4839	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:13.512274
4840	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:13.518061
4841	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:13.582587
4842	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:13.588478
4843	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:13.653258
4844	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:13.659137
4845	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:13.723992
4846	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:13.729806
4847	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:13.794042
4848	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:13.79991
4849	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:13.864591
4850	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:13.87121
4851	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:13.937288
4852	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:13.942794
4853	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:14.008439
4854	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:14.050741
4855	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:14.16224
4856	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:14.168265
4857	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:14.232834
4858	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:14.238489
4859	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:14.302265
4860	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:14.308526
4861	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:14.373117
4862	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:14.380424
4863	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:14.445004
4864	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:14.450688
4865	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:14.515069
4866	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:14.521348
4867	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:14.595062
4868	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:14.601528
4869	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:14.69852
4870	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:14.703447
4871	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:14.750361
4872	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:14.758615
4873	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:14.800532
4874	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:14.805031
4875	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:14.841172
4876	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:14.84519
4877	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:14.875418
4878	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:14.879269
4879	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:14.910328
4880	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:14.91435
4881	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:14.947827
4882	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:14.951831
4883	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:15.016655
4884	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:15.022064
4885	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:15.087267
4886	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:15.093295
4887	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:15.158287
4888	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:15.164251
4889	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:15.231605
4890	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:15.237154
4891	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:15.303097
4892	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:15.308785
4893	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:15.373634
4894	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:15.379521
4895	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:15.446426
4896	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:15.452306
4897	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:15.51767
4898	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:15.523949
4899	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:15.589091
4900	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:15.595017
4901	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:15.660833
4902	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:15.666637
4903	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:15.73181
4904	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:15.737572
4905	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:15.803211
4906	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:15.809085
4907	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:15.874117
4908	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:15.879784
4909	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:15.945502
4910	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:15.951535
4911	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:16.017258
4912	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:16.023106
4913	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:16.089494
4914	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:16.095199
4915	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:16.160544
4916	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:16.166582
4917	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:16.230372
4918	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:16.23592
4919	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:16.308543
4920	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:16.314282
4921	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:16.384974
4922	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:16.391144
4923	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:16.455643
4924	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:16.46136
4925	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:16.533197
4926	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:16.538909
4927	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:16.615083
4928	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:16.620657
4929	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:16.692891
4930	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:16.698616
4931	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:16.770865
4932	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:16.776316
4933	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:16.866732
4934	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:16.871713
4935	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:16.919242
4936	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:16.926412
4937	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:16.961238
4938	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:16.96704
4939	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:17.041856
4940	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:17.048017
4941	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:17.117547
4942	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:17.124166
4943	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:17.190137
4944	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:17.195792
4945	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:17.267235
4946	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:17.273075
4947	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:17.339432
4948	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:17.345259
4949	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:17.410338
4950	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:17.41608
4951	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:17.481214
4952	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:17.487096
4953	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:17.552407
4954	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:17.558355
4955	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:17.625558
4956	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:17.631508
4957	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:17.697038
4958	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:17.70289
4959	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:17.768374
4960	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:17.77435
4961	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:17.840051
4962	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:17.84605
4963	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:17.911439
4964	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:17.917231
4965	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:17.982837
4966	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:17.988503
4967	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:18.053976
4968	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:18.059666
4969	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:18.125182
4970	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:18.131179
4971	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:18.21138
4972	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:18.215258
4973	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:18.267187
4974	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:18.271937
4975	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:18.323386
4976	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:18.328424
4977	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:18.393381
4978	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:18.399175
4979	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:18.464461
4980	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:18.470406
4981	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:18.535929
4982	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:18.541975
4983	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:18.607424
4984	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:18.613295
4985	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:18.678597
4986	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:18.684549
4987	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:18.749988
4988	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:18.755516
4989	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:18.820802
4990	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:18.826498
4991	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:18.892441
4992	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:18.898175
4993	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:18.963708
4994	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:18.970004
4995	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:19.035555
4996	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:19.041471
4997	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:19.11148
4998	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:19.117623
4999	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:19.203832
5000	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:19.207279
5001	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:19.275384
5002	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:19.281269
5003	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:19.346799
5004	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:19.352515
5005	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:19.417743
5006	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:19.425223
5007	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:19.491825
5008	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:19.497631
5009	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:19.563175
5010	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:19.569196
5011	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:19.635196
5012	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:19.641165
5013	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:19.706628
5014	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:19.712431
5015	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:19.778299
5016	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:19.784067
5017	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:19.849425
5018	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:19.85552
5019	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:19.920584
5020	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:19.926373
5021	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:19.991421
5022	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:19.997211
5023	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:20.063126
5024	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:20.068916
5025	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:20.1342
5026	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:20.140028
5027	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:20.217391
5028	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:20.22312
5029	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:20.288276
5030	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:20.294029
5031	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:20.359139
5032	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:20.365144
5033	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:20.431786
5034	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:20.437567
5035	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:20.502719
5036	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:20.508435
5037	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:20.573739
5038	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:20.579428
5039	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:20.645019
5040	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:20.650734
5041	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:20.715738
5042	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:20.721717
5043	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:20.786794
5044	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:20.792445
5045	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:20.857665
5046	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:20.863363
5047	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:20.928401
5048	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:20.934239
5049	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:21.002811
5050	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:21.008788
5051	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:21.073583
5052	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:21.079201
5053	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:21.144847
5054	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:21.150814
5055	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:21.216214
5056	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:21.222085
5057	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:21.291179
5058	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:21.296887
5059	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:21.365419
5060	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:21.371245
5061	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:21.436892
5062	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:21.442814
5063	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:21.507873
5064	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:21.513606
5065	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:21.579265
5066	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:21.585217
5067	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:21.650737
5068	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:21.656656
5069	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:21.722013
5070	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:21.727631
5071	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:21.792797
5072	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:21.798809
5073	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:21.864255
5074	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:21.870314
5075	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:21.936652
5076	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:21.942466
5077	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:22.024023
5078	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:22.028095
5079	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:22.079061
5080	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:22.083951
5081	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:22.149447
5082	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:22.155396
5083	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:22.220911
5084	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:22.226664
5085	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:22.292679
5086	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:22.298371
5087	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:22.364402
5088	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:22.36995
5089	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:22.440925
5090	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:22.446784
5091	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:22.518411
5092	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:22.5242
5093	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:22.597043
5094	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:22.602712
5095	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:22.675473
5096	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:22.681124
5097	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:22.748107
5098	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:22.754281
5099	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:22.823132
5100	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:22.828744
5101	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:22.899866
5102	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:22.905745
5103	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:22.97173
5104	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:22.97717
5105	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:23.047849
5106	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:23.053412
5107	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:23.133511
5108	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:23.139612
5109	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:23.211948
5110	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:23.217555
5111	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:23.290558
5112	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:23.298142
5113	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:23.387367
5114	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:23.392063
5115	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:23.439192
5116	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:23.443629
5117	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:23.47985
5118	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:23.484343
5119	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:23.51699
5120	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:23.520942
5121	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:23.551362
5122	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:23.55639
5123	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:23.623425
5124	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:23.632836
5125	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:23.699589
5126	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:23.705671
5127	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:23.770842
5128	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:23.776635
5129	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:23.841836
5130	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:23.847638
5131	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:23.912424
5132	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:23.918348
5133	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:23.983177
5134	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:23.989212
5135	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:24.054196
5136	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:24.060177
5137	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:24.126017
5138	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:24.1322
5139	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:24.203024
5140	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:24.209252
5141	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:24.274271
5142	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:24.280598
5143	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:24.345812
5144	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:24.353134
5145	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:24.419057
5146	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:24.425002
5147	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:24.490292
5148	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:24.496134
5149	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:24.561568
5150	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:24.569615
5151	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:24.635154
5152	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:24.641441
5153	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:24.706143
5154	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:24.712045
5155	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:24.812654
5156	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:24.817529
5157	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:24.847633
5158	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:24.850785
5159	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:24.880725
5160	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:24.883937
5161	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:24.913525
5162	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:24.916775
5163	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:24.94704
5164	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:24.950241
5165	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:24.980157
5166	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:24.984064
5167	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:25.01483
5168	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:25.018709
5169	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:25.049111
5170	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:25.053045
5171	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:25.083577
5172	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:25.087965
5173	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:25.139301
5174	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:25.144821
5175	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:25.212532
5176	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:25.218167
5177	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:25.290839
5178	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:25.296397
5179	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:25.362647
5180	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:25.368204
5181	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:25.43299
5182	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:25.438613
5183	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:25.504467
5184	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:25.510589
5185	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:25.579194
5186	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:25.585701
5187	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:25.653815
5188	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:25.659122
5189	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:25.730181
5190	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:25.736488
5191	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:25.802657
5192	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:25.808168
5193	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:25.873356
5194	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:25.879052
5195	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:25.943629
5196	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:25.950249
5197	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:26.015476
5198	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:26.02116
5199	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:26.08584
5200	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:26.091453
5201	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:26.156001
5202	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:26.162149
5203	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:26.228536
5204	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:26.234204
5205	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:26.303596
5206	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:26.309995
5207	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:26.374662
5208	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:26.380382
5209	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:26.445704
5210	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:26.451631
5211	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:26.516833
5212	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:26.523059
5213	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:26.588282
5214	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:26.594066
5215	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:26.659287
5216	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:26.665613
5217	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:26.731266
5218	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:26.736955
5219	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:26.802216
5220	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:26.807914
5221	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:26.87259
5222	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:26.878436
5223	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:26.944076
5224	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:26.949887
5225	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:27.016107
5226	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:27.022092
5227	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:27.08833
5228	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:27.093961
5229	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:27.159161
5230	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:27.165122
5231	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:27.230465
5232	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:27.235956
5233	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:27.300495
5234	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:27.306377
5235	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:27.371281
5236	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:27.376989
5237	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:27.442641
5238	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:27.448263
5239	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:27.513439
5240	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:27.519075
5241	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:27.584362
5242	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:27.590067
5243	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:27.656172
5244	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:27.66227
5245	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:27.728526
5246	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:27.735188
5247	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:27.802705
5248	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:27.808942
5249	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:27.880078
5250	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:27.886588
5251	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:27.953085
5252	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:27.958789
5253	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:28.024065
5254	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:28.029928
5255	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:28.09495
5256	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:28.100542
5257	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:28.165267
5258	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:28.171635
5259	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:28.23709
5260	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:28.242509
5261	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:28.31457
5262	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:28.320084
5263	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:28.410913
5264	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:28.411861
5265	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:28.441795
5266	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:28.445012
5267	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:28.477635
5268	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:28.480857
5269	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:28.512731
5270	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:28.516212
5271	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:28.548717
5272	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:28.551924
5273	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:28.581576
5274	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:28.584585
5275	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:28.654381
5276	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:28.659382
5277	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:28.710897
5278	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:28.715709
5279	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:28.771813
5280	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:28.776661
5281	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:28.827888
5282	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:28.832665
5283	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:28.883916
5284	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:28.888867
5285	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:28.939531
5286	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:28.944339
5287	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:28.995472
5288	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:29.000478
5289	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:29.065335
5290	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:29.071387
5291	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:29.137923
5292	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:29.143531
5293	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:29.227946
5294	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:29.233452
5295	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:29.264611
5296	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:29.268948
5297	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:29.328029
5298	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:29.335719
5299	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:29.401846
5300	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:29.407557
5301	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:29.479127
5302	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:29.485033
5303	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:29.556952
5304	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:29.569859
5305	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:29.663614
5306	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:29.670552
5307	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:29.75964
5308	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:29.767541
5309	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:29.811828
5310	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:29.815608
5311	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:29.854364
5312	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:29.858105
5313	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:29.899563
5314	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:29.903138
5315	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:29.968242
5316	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:29.973036
5317	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:30.009984
5318	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:30.01368
5319	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:30.081249
5320	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:30.086093
5321	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:30.158401
5322	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:30.163523
5323	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:30.213671
5324	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:30.215054
5325	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:30.277194
5326	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:30.28302
5327	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:30.349912
5328	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:30.355954
5329	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:30.421442
5330	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:30.427421
5331	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:30.492258
5332	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:30.498396
5333	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:30.563197
5334	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:30.574967
5335	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:30.640929
5336	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:30.64648
5337	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:30.712207
5338	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:30.718039
5339	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:30.785117
5340	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:30.790949
5341	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:30.856493
5342	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:30.862479
5343	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:30.927942
5344	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:30.933808
5345	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:31.001559
5346	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:31.00809
5347	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:31.073224
5348	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:31.078916
5349	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:31.144039
5350	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:31.149963
5351	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:31.218593
5352	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:31.224351
5353	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:31.289646
5354	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:31.295699
5355	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:31.361323
5356	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:31.367916
5357	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:31.434222
5358	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:31.440373
5359	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:31.506071
5360	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:31.511661
5361	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:31.577054
5362	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:31.582516
5363	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:31.647496
5364	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:31.653139
5365	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:31.720093
5366	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:31.725781
5367	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:31.790054
5368	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:31.79573
5369	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:31.859991
5370	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:31.865792
5371	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:31.930091
5372	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:31.937001
5373	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:32.017307
5374	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:32.023432
5375	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:32.088823
5376	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:32.095357
5377	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:32.162294
5378	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:32.168525
5379	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:32.233983
5380	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:32.239696
5381	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:32.312464
5382	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:32.317909
5383	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:32.38149
5384	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:32.387012
5385	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:32.451863
5386	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:32.457667
5387	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:32.522341
5388	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:32.528263
5389	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:32.59339
5390	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:32.599579
5391	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:32.66469
5392	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:32.670687
5393	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:32.735477
5394	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:32.741127
5395	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:32.807011
5396	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:32.813153
5397	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:32.877548
5398	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:32.883629
5399	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:32.949314
5400	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:32.955404
5401	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:33.020074
5402	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:33.026341
5403	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:33.091611
5404	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:33.098704
5405	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:33.163815
5406	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:33.169609
5407	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:33.234628
5408	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:33.240201
5409	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:33.304624
5410	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:33.310431
5411	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:33.374955
5412	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:33.380739
5413	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:33.445723
5414	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:33.451806
5415	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:33.52098
5416	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:33.527008
5417	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:33.592007
5418	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:33.597983
5419	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:33.663793
5420	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:33.669679
5421	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:33.735478
5422	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:33.741227
5423	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:33.806479
5424	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:33.812425
5425	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:33.877218
5426	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:33.883186
5427	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:33.948191
5428	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:33.95407
5429	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:34.019258
5430	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:34.025195
5431	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:34.090089
5432	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:34.096148
5433	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:34.161325
5434	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:34.170579
5435	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:34.238262
5436	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:34.244187
5437	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:34.335415
5438	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:34.344375
5439	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:34.417099
5440	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:34.421666
5441	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:34.484057
5442	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:34.491899
5443	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:34.594571
5444	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:34.598681
5445	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:34.64128
5446	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:34.6444
5447	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:34.673719
5448	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:34.67695
5449	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:34.706896
5450	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:34.710603
5451	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:34.775278
5452	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:34.781264
5453	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:34.846298
5454	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:34.851957
5455	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:34.916644
5456	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:34.922559
5457	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:34.989517
5458	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:34.995259
5459	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:35.059792
5460	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:35.065518
5461	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:35.130832
5462	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:35.137114
5463	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:35.201607
5464	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:35.207366
5465	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:35.272713
5466	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:35.278625
5467	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:35.343335
5468	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:35.349296
5469	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:35.418192
5470	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:35.423915
5471	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:35.488796
5472	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:35.494598
5473	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:35.559596
5474	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:35.565813
5475	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:35.630281
5476	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:35.636155
5477	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:35.701589
5478	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:35.707366
5479	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:35.772221
5480	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:35.777977
5481	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:35.843093
5482	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:35.848927
5483	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:35.913946
5484	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:35.919531
5485	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:35.984369
5486	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:35.992673
5487	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:36.057282
5488	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:36.063538
5489	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:36.128348
5490	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:36.134104
5491	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:36.200726
5492	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:36.206412
5493	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:36.270814
5494	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:36.27634
5495	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:36.341716
5496	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:36.347423
5497	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:36.412038
5498	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:36.41835
5499	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:36.483858
5500	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:36.48981
5501	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:36.561972
5502	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:36.568368
5503	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:36.640434
5504	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:36.646672
5505	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:36.719565
5506	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:36.723991
5507	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:36.787108
5508	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:36.792951
5509	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:36.857336
5510	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:36.863121
5511	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:36.92783
5512	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:36.933643
5513	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:36.998625
5514	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:37.004435
5515	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:37.069235
5516	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:37.075532
5517	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:37.143414
5518	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:37.151688
5519	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:37.216648
5520	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:37.222335
5521	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:37.294794
5522	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:37.301031
5523	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:37.373007
5524	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:37.378797
5525	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:37.449838
5526	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:37.455622
5527	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:37.526029
5528	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:37.531931
5529	2	Starting analysis	started	5	Initializing PDF processing...	{}	2025-08-05 14:55:37.609253
5530	2	Connecting to GPU	started	10	Establishing connection to processing server...	{}	2025-08-05 14:55:37.614982
5531	2	Sending to GPU for processing	started	5	Task picked up by queue processor	{}	2025-08-05 16:58:05.673245
5533	2	Sending to GPU for processing	started	5	Task picked up by queue processor	{}	2025-08-05 16:59:55.814341
5535	2	Sending to GPU for processing	started	5	Task picked up by queue processor	{}	2025-08-05 17:29:56.86151
5536	2	GPU processing started	started	10	Task sent to GPU successfully	{}	2025-08-05 17:31:58.635618
5539	2	Sending to GPU for processing	started	5	Task picked up by queue processor	{}	2025-08-05 18:01:58.848098
5540	2	GPU processing started	started	10	Task sent to GPU successfully	{}	2025-08-05 18:03:59.378347
5543	2	Sending to GPU for processing	started	5	Task picked up by queue processor	{}	2025-08-05 18:34:00.862222
5562	7	Sending to GPU for processing	started	5	Task picked up by queue processor	{}	2025-08-05 20:05:44.867079
5563	7	GPU processing started	started	10	Task sent to GPU successfully	{}	2025-08-05 20:06:20.868077
5566	8	Sending to GPU for processing	started	5	Task picked up by queue processor	{}	2025-08-05 20:12:05.393399
5567	8	GPU processing started	started	10	Task sent to GPU successfully	{}	2025-08-05 20:13:26.698875
5569	9	Sending to GPU for processing	started	5	Task picked up by queue processor	{}	2025-08-05 20:21:06.463067
5570	9	GPU processing started	started	10	Task sent to GPU successfully	{}	2025-08-05 20:23:02.255099
5588	14	Sending to GPU for processing	started	5	Task picked up by queue processor	{}	2025-08-05 23:06:12.443865
5589	14	Visual Analysis	started	10	Analyzing slides and extracting content	{}	2025-08-05 23:06:12.458053
5590	14	Visual Analysis Complete	started	30	Slides analyzed, starting extraction	{}	2025-08-05 23:06:15.404152
5591	14	Data Extraction	started	40	Extracting company details and classification	{}	2025-08-05 23:06:15.412214
5592	14	Extraction Complete	started	60	Company data extracted, starting template analysis	{}	2025-08-05 23:06:17.421089
5593	14	Template Analysis	started	70	Running AI analysis with healthcare templates	{}	2025-08-05 23:06:17.436432
5594	14	Analysis Complete	started	95	Finalizing results	{}	2025-08-05 23:06:17.54045
5597	16	Sending to GPU for processing	started	5	Task picked up by queue processor	{}	2025-08-05 23:14:27.318505
5598	16	Visual Analysis	started	10	Analyzing slides and extracting content	{}	2025-08-05 23:14:27.329634
5599	16	Visual Analysis Complete	started	30	Slides analyzed, starting extraction	{}	2025-08-05 23:14:30.298691
5600	16	Data Extraction	started	40	Extracting company details and classification	{}	2025-08-05 23:14:30.307675
5601	16	Extraction Complete	started	60	Company data extracted, starting template analysis	{}	2025-08-05 23:14:32.316378
5602	16	Template Analysis	started	70	Running AI analysis with healthcare templates	{}	2025-08-05 23:14:32.325218
5603	16	Analysis Complete	started	95	Finalizing results	{}	2025-08-05 23:14:32.412444
5625	14	Sending to GPU for processing	started	5	Task picked up by queue processor	{}	2025-08-05 23:36:17.983658
5626	14	Visual Analysis	started	10	Analyzing slides and extracting content	{}	2025-08-05 23:36:17.993719
5627	14	Visual Analysis Complete	started	30	Slides analyzed, starting extraction	{}	2025-08-05 23:36:20.917588
5628	14	Data Extraction	started	40	Extracting company details and classification	{}	2025-08-05 23:36:20.924784
5629	14	Extraction Complete	started	60	Company data extracted, starting template analysis	{}	2025-08-05 23:36:22.932503
5630	14	Template Analysis	started	70	Running AI analysis with healthcare templates	{}	2025-08-05 23:36:22.939514
5631	14	Analysis Complete	started	95	Finalizing results	{}	2025-08-05 23:36:23.022057
5632	19	Sending to GPU for processing	started	5	Task picked up by queue processor	{}	2025-08-06 06:57:31.287018
5633	19	Visual Analysis	started	10	Analyzing slides and extracting content	{}	2025-08-06 06:57:31.296548
5634	19	Visual Analysis Complete	started	30	Slides analyzed, starting extraction	{}	2025-08-06 06:57:34.251728
5635	19	Data Extraction	started	40	Extracting company details and classification	{}	2025-08-06 06:57:34.258847
5636	19	Extraction Complete	started	60	Company data extracted, starting template analysis	{}	2025-08-06 06:57:36.266232
5637	19	Template Analysis	started	70	Running AI analysis with healthcare templates	{}	2025-08-06 06:57:36.273439
5638	19	Analysis Complete	started	95	Finalizing results	{}	2025-08-06 06:57:36.364568
5639	20	Sending to GPU for processing	started	5	Task picked up by queue processor	{}	2025-08-06 07:00:51.583614
5640	20	Visual Analysis	started	10	Analyzing slides and extracting content	{}	2025-08-06 07:00:51.59434
5641	20	Visual Analysis Complete	started	30	Slides analyzed, starting extraction	{}	2025-08-06 07:00:59.687324
5642	20	Data Extraction	started	40	Extracting company details and classification	{}	2025-08-06 07:00:59.695452
5643	20	Extraction Complete	started	60	Company data extracted, starting template analysis	{}	2025-08-06 07:01:01.705337
5644	20	Template Analysis	started	70	Running AI analysis with healthcare templates	{}	2025-08-06 07:01:01.713218
5645	20	Analysis Complete	started	95	Finalizing results	{}	2025-08-06 07:01:01.777722
5646	21	Sending to GPU for processing	started	5	Task picked up by queue processor	{}	2025-08-06 07:14:07.974206
5647	21	Visual Analysis	started	10	Analyzing slides and extracting content	{}	2025-08-06 07:14:07.984548
5648	21	Visual Analysis Complete	started	30	Slides analyzed, starting extraction	{}	2025-08-06 07:14:10.442649
5649	21	Data Extraction	started	40	Extracting company details and classification	{}	2025-08-06 07:14:10.450127
5650	21	Extraction Complete	started	60	Company data extracted, starting template analysis	{}	2025-08-06 07:14:12.457532
5651	21	Template Analysis	started	70	Running AI analysis with healthcare templates	{}	2025-08-06 07:14:12.463642
5652	21	Analysis Complete	started	95	Finalizing results	{}	2025-08-06 07:18:09.811533
5653	22	Sending to GPU for processing	started	5	Task picked up by queue processor	{}	2025-08-06 07:19:54.956282
5654	22	Visual Analysis	started	10	Analyzing slides and extracting content	{}	2025-08-06 07:19:54.966721
5655	22	Visual Analysis Complete	started	30	Slides analyzed, starting extraction	{}	2025-08-06 07:19:57.494227
5656	22	Data Extraction	started	40	Extracting company details and classification	{}	2025-08-06 07:19:57.502797
5659	22	Analysis Complete	started	95	Finalizing results	{}	2025-08-06 07:23:46.425012
5660	23	Sending to GPU for processing	started	5	Task picked up by queue processor	{}	2025-08-06 10:33:48.425139
5657	22	Extraction Complete	started	60	Company data extracted, starting template analysis	{}	2025-08-06 07:19:59.509462
5663	23	Data Extraction	started	40	Extracting company details and classification	{}	2025-08-06 10:33:55.2518
5665	23	Template Analysis	started	70	Running AI analysis with healthcare templates	{}	2025-08-06 10:33:57.267446
5658	22	Template Analysis	started	70	Running AI analysis with healthcare templates	{}	2025-08-06 07:19:59.517385
5661	23	Visual Analysis	started	10	Analyzing slides and extracting content	{}	2025-08-06 10:33:48.434935
5662	23	Visual Analysis Complete	started	30	Slides analyzed, starting extraction	{}	2025-08-06 10:33:55.244021
5664	23	Extraction Complete	started	60	Company data extracted, starting template analysis	{}	2025-08-06 10:33:57.259861
5666	23	Analysis Complete	started	95	Finalizing results	{}	2025-08-06 10:33:57.353338
5667	24	Sending to GPU for processing	started	5	Task picked up by queue processor	{}	2025-08-06 12:21:09.140282
5668	24	Visual Analysis	started	10	Analyzing slides and extracting content	{}	2025-08-06 12:21:09.150924
\.


--
-- Data for Name: processing_queue; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.processing_queue (id, pitch_deck_id, task_type, status, priority, file_path, company_id, processing_options, progress_percentage, current_step, progress_message, created_at, started_at, completed_at, retry_count, max_retries, next_retry_at, last_error, error_count, locked_by, locked_at, lock_expires_at, results_file_path, processing_metadata, template_id_used, template_source) FROM stdin;
7	138	pdf_analysis	completed	1	uploads/ismaning/04c6d465-2485-4e8f-b03e-9de7c1e58923/Phiggle_PreSend_Slides.pdf	ismaning	{"user_id": 12, "upload_timestamp": "2025-08-05T20:05:42.857488", "generate_feedback": true, "generate_thumbnails": true}	100	Analysis Complete	PDF analysis completed successfully	2025-08-05 20:05:42.865704	2025-08-05 20:05:44.867079	2025-08-05 20:15:29.835696	0	3	\N	\N	0	\N	\N	\N	\N	{}	\N	\N
16	140	pdf_analysis	completed	1	uploads/ismaning/62dcb365-ef28-4b55-ba12-ec676d5a48b4/Apersys_Pitch_non-confidential.pdf	ismaning	{}	100	Analysis Complete	Finalizing results	2025-08-05 23:14:22.340772	2025-08-05 23:14:27.318505	2025-08-05 23:14:32.422335	0	3	\N	\N	0	\N	\N	\N	\N	{}	\N	\N
19	140	pdf_analysis	completed	1	uploads/ismaning/62dcb365-ef28-4b55-ba12-ec676d5a48b4/Apersys_Pitch_non-confidential.pdf	ismaning	{}	100	Analysis Complete	Finalizing results	2025-08-06 06:57:27.157551	2025-08-06 06:57:31.287018	2025-08-06 06:57:36.372178	0	3	\N	\N	0	\N	\N	\N	\N	{}	\N	\N
22	119	pdf_analysis	completed	1	projects/dojo/uploads/4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck.pdf	119	{"use_single_template": false}	100	Analysis Complete	Finalizing results	2025-08-06 07:19:52.276175	2025-08-06 07:19:54.956282	2025-08-06 07:23:46.432597	0	3	\N	\N	0	\N	\N	\N	\N	{}	\N	\N
8	139	pdf_analysis	completed	1	uploads/ismaning/bdf9e8f9-12e2-44a1-a2bc-8f4b8379a6dc/Oberit-Pitch-Deck-Dec-2024-2.pdf	ismaning	{"user_id": 12, "upload_timestamp": "2025-08-05T20:11:00.722616", "generate_feedback": true, "generate_thumbnails": true}	100	Analysis Complete	PDF analysis completed successfully	2025-08-05 20:11:00.732159	2025-08-05 20:12:05.393399	2025-08-05 20:15:29.835696	0	3	\N	\N	0	\N	\N	\N	\N	{}	\N	\N
23	143	pdf_analysis	completed	1	uploads/ismaning/b0bf6d69-29c5-4c0f-8dd5-e3450511f80f/20250310_AskMika_csi.pdf	ismaning	{"user_id": 12, "upload_timestamp": "2025-08-06T10:33:44.114239", "generate_feedback": true, "generate_thumbnails": true}	100	Analysis Complete	Finalizing results	2025-08-06 10:33:44.122178	2025-08-06 10:33:48.425139	2025-08-06 10:33:57.360686	0	3	\N	\N	0	\N	\N	\N	\N	{}	\N	\N
20	120	pdf_analysis	completed	1	projects/dojo/uploads/30ca13f27ff44fe08fdda5c7e38996e5_Fusix Biotech_2025v2.pdf	dojo	{}	100	Analysis Complete	Finalizing results	2025-08-06 07:00:47.309979	2025-08-06 07:00:51.583614	2025-08-06 07:01:01.786619	0	3	\N	\N	0	\N	\N	\N	\N	{}	\N	\N
21	119	pdf_analysis	completed	1	projects/dojo/uploads/4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck.pdf	dojo	{}	100	Analysis Complete	Finalizing results	2025-08-06 07:14:06.410629	2025-08-06 07:14:07.974206	2025-08-06 07:18:09.819923	0	3	\N	\N	0	\N	\N	\N	\N	{}	\N	\N
24	144	pdf_analysis	failed	1	uploads/ismaning/6e85c15e-a872-443e-b208-22bbfcbfc0ee/Heartful-Sprout---Pitch-Deck.pdf	ismaning	{"user_id": 12, "upload_timestamp": "2025-08-06T12:21:09.118385", "generate_feedback": true, "generate_thumbnails": true}	10	Visual Analysis	Analyzing slides and extracting content	2025-08-06 12:21:09.124776	2025-08-06 12:21:09.140282	2025-08-06 12:21:09.162054	0	3	\N	Failed to send task to GPU server	2	\N	\N	\N	\N	{}	\N	\N
9	140	pdf_analysis	completed	1	uploads/ismaning/62dcb365-ef28-4b55-ba12-ec676d5a48b4/Apersys_Pitch_non-confidential.pdf	ismaning	{"user_id": 12, "upload_timestamp": "2025-08-05T20:21:02.360939", "generate_feedback": true, "generate_thumbnails": true}	10	GPU processing started	Task sent to GPU successfully	2025-08-05 20:21:02.36993	2025-08-05 20:21:06.463067	2025-08-05 20:23:02.240845	0	3	\N	\N	0	\N	\N	\N	results/job_140_1754425382_results.json	{}	\N	\N
14	140	pdf_analysis	completed	1	uploads/ismaning/62dcb365-ef28-4b55-ba12-ec676d5a48b4/Apersys_Pitch_non-confidential.pdf	ismaning	{}	100	Analysis Complete	Finalizing results	2025-08-05 23:06:08.9534	2025-08-05 23:06:12.443865	2025-08-05 23:36:23.028687	0	3	\N	\N	0	\N	\N	\N	\N	{}	\N	\N
2	121	pdf_analysis	failed	1	/mnt/CPU-GPU/uploads/ismaning/71ab3c38-61c3-4ad1-a57e-7814bd0421f6/Genevation-Pitch-deck.pdf	ismaning	{"test": true}	5	Sending to GPU for processing	Task picked up by queue processor	2025-08-05 14:47:58.637789	2025-08-05 16:59:55.814341	2025-08-05 18:35:10.165507	0	3	\N	Failed to send task to GPU server	2	\N	\N	\N	\N	{}	\N	\N
\.


--
-- Data for Name: processing_servers; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.processing_servers (id, server_type, status, last_heartbeat, capabilities, current_load, max_concurrent_tasks, created_at, updated_at) FROM stdin;
happy-heart-shines-fin-01-483805-807f1f4e	cpu	active	2025-08-06 11:44:16.614488	{"pdf_analysis": true, "gpu_available": false, "max_concurrent": 3}	0	3	2025-08-06 11:44:16.614488	2025-08-06 11:44:16.614488
\.


--
-- Data for Name: production_projects; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.production_projects (id, company_id, project_name, funding_round, current_stage_id, funding_sought, healthcare_sector_id, company_offering, project_metadata, is_active, created_at, updated_at, tags, is_test) FROM stdin;
\.


--
-- Data for Name: project_documents; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.project_documents (id, project_id, document_type, file_name, file_path, original_filename, file_size, processing_status, extracted_data, analysis_results_path, uploaded_by, upload_date, is_active) FROM stdin;
45	27	pitch_deck	2025_Lilio Investment Deck.pdf	projects/dojo/uploads/4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck.pdf	2025_Lilio Investment Deck.pdf	\N	completed	\N	\N	1	2025-08-03 11:10:09.685038	t
46	27	analysis_results	Lilio_analysis_results.json	template_processed	Lilio_analysis_results.json	\N	completed	\N	\N	1	2025-08-03 11:10:09.689012	t
47	29	pitch_deck	LEM-Surgical-Opportunity-Overview.pdf	uploads/ismaning/a361d599-2c1a-4d3a-887e-914722297bcd/LEM-Surgical-Opportunity-Overview.pdf	LEM-Surgical-Opportunity-Overview.pdf	\N	completed	\N	\N	12	2025-08-03 18:13:55.177208	t
48	29	analysis_results	ismaning_analysis_results.json	/mnt/CPU-GPU/results/job_122_1754244835_results.json	ismaning_analysis_results.json	\N	completed	\N	\N	12	2025-08-03 18:13:55.179232	t
49	29	pitch_deck	IntelliPharm-Pitch-Deck-Full-.pdf	uploads/ismaning/14555de3-e19d-4236-afa3-046d9602c39b/IntelliPharm-Pitch-Deck-Full-.pdf	IntelliPharm-Pitch-Deck-Full-.pdf	\N	completed	\N	\N	12	2025-08-04 09:55:22.821111	t
50	29	analysis_results	ismaning_analysis_results.json	/mnt/CPU-GPU/results/job_123_1754301322_results.json	ismaning_analysis_results.json	\N	completed	\N	\N	12	2025-08-04 09:55:22.823282	t
51	29	pitch_deck	MOLECL-intro-.pdf	uploads/ismaning/6c074f1c-03de-4ab3-9078-3db1d6f95e14/MOLECL-intro-.pdf	MOLECL-intro-.pdf	\N	completed	\N	\N	12	2025-08-04 10:20:47.377416	t
52	29	analysis_results	ismaning_analysis_results.json	/mnt/CPU-GPU/results/job_124_1754302847_results.json	ismaning_analysis_results.json	\N	completed	\N	\N	12	2025-08-04 10:20:47.379116	t
53	29	pitch_deck	Auric_Pre_Seed_4_Feb2025.pdf	uploads/ismaning/cac8db65-56b3-464e-8829-313c51b9e16c/Auric_Pre_Seed_4_Feb2025.pdf	Auric_Pre_Seed_4_Feb2025.pdf	\N	completed	\N	\N	12	2025-08-04 10:51:57.78813	t
54	29	analysis_results	ismaning_analysis_results.json	/mnt/CPU-GPU/results/job_125_1754304717_results.json	ismaning_analysis_results.json	\N	completed	\N	\N	12	2025-08-04 10:51:57.790636	t
55	29	pitch_deck	HemoVisionAI-Pitch-Deck-For-Investors---Phased-Approach.pdf	uploads/ismaning/34699b44-e6cc-4b93-a7fc-1a1a5e0aee75/HemoVisionAI-Pitch-Deck-For-Investors---Phased-Approach.pdf	HemoVisionAI-Pitch-Deck-For-Investors---Phased-Approach.pdf	\N	completed	\N	\N	12	2025-08-04 11:18:32.354402	t
56	29	analysis_results	ismaning_analysis_results.json	/mnt/CPU-GPU/results/job_126_1754306312_results.json	ismaning_analysis_results.json	\N	completed	\N	\N	12	2025-08-04 11:18:32.356402	t
57	29	pitch_deck	Genevation-Pitch-deck.pdf	uploads/ismaning/71ab3c38-61c3-4ad1-a57e-7814bd0421f6/Genevation-Pitch-deck.pdf	Genevation-Pitch-deck.pdf	\N	completed	\N	\N	12	2025-08-04 11:36:20.803514	t
58	29	analysis_results	ismaning_analysis_results.json	/mnt/CPU-GPU/results/job_127_1754307380_results.json	ismaning_analysis_results.json	\N	completed	\N	\N	12	2025-08-04 11:36:20.805254	t
59	29	pitch_deck	HealthQuest2025.pptx.pdf	uploads/ismaning/9ad679c6-f815-48c7-a388-53c90d7f7930/HealthQuest2025.pptx.pdf	HealthQuest2025.pptx.pdf	\N	completed	\N	\N	12	2025-08-05 08:02:21.678308	t
60	29	analysis_results	ismaning_analysis_results.json	/mnt/CPU-GPU/results/job_128_1754380941_results.json	ismaning_analysis_results.json	\N	completed	\N	\N	12	2025-08-05 08:02:21.680865	t
61	29	pitch_deck	Sense4Med---investordeck.pdf.pdf	uploads/ismaning/c6654e1e-9ae6-4b80-9b6f-158b70dc8995/Sense4Med---investordeck.pdf.pdf	Sense4Med---investordeck.pdf.pdf	\N	completed	\N	\N	12	2025-08-05 08:19:50.337112	t
62	29	analysis_results	ismaning_analysis_results.json	/mnt/CPU-GPU/results/job_129_1754381990_results.json	ismaning_analysis_results.json	\N	completed	\N	\N	12	2025-08-05 08:19:50.339426	t
63	29	pitch_deck	NEUROSTECH-pitch-NOV24.pdf	uploads/ismaning/3dcf040c-7a6b-4974-aefa-1ae603f191ce/NEUROSTECH-pitch-NOV24.pdf	NEUROSTECH-pitch-NOV24.pdf	\N	completed	\N	\N	12	2025-08-05 11:33:48.959219	t
64	29	analysis_results	ismaning_analysis_results.json	/mnt/CPU-GPU/results/job_130_1754393628_results.json	ismaning_analysis_results.json	\N	completed	\N	\N	12	2025-08-05 11:33:48.961409	t
65	29	pitch_deck	IntelliPharm-Pitch-Deck-Full-.pdf	uploads/ismaning/87eee5f8-e14d-43a9-b658-6f6b87b2aaa5/IntelliPharm-Pitch-Deck-Full-.pdf	IntelliPharm-Pitch-Deck-Full-.pdf	\N	completed	\N	\N	12	2025-08-05 15:12:52.784413	t
66	29	analysis_results	ismaning_analysis_results.json	/mnt/CPU-GPU/results/job_132_1754406772_results.json	ismaning_analysis_results.json	\N	completed	\N	\N	12	2025-08-05 15:12:52.7867	t
67	29	pitch_deck	Montuno-Health-2025-Investor-Deck.pdf	uploads/ismaning/e1a72387-dae5-4598-ae14-c94d26522b36/Montuno-Health-2025-Investor-Deck.pdf	Montuno-Health-2025-Investor-Deck.pdf	\N	completed	\N	\N	12	2025-08-05 15:35:25.005121	t
68	29	analysis_results	ismaning_analysis_results.json	/mnt/CPU-GPU/results/job_133_1754408124_results.json	ismaning_analysis_results.json	\N	completed	\N	\N	12	2025-08-05 15:35:25.006918	t
\.


--
-- Data for Name: project_interactions; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.project_interactions (id, project_id, interaction_type, title, content, document_id, created_by, status, interaction_metadata, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: project_invitations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.project_invitations (id, invitation_token, project_id, email, invited_by_id, status, created_at, accepted_at, expires_at, accepted_by_id) FROM stdin;
1	BJxvlM3B0mGJEpouIW08aK0mvF9Oa90E	28	raminassadollahi@gmail.com	1	pending	2025-08-03 15:02:41.671054	\N	2025-08-10 15:02:41.669427	\N
\.


--
-- Data for Name: project_members; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.project_members (id, project_id, user_id, role, added_by_id, added_at) FROM stdin;
1	28	1	owner	1	2025-08-03 15:02:41.65354
\.


--
-- Data for Name: project_stages; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.project_stages (id, project_id, stage_name, stage_order, status, stage_metadata, started_at, completed_at, created_at, stage_template_id, stage_code) FROM stdin;
309	27	Deck Submission & Feedback	1	active	{"document_types": ["pitch_deck"], "allows_documents": true, "feedback_required": true}	2025-08-03 11:10:09.671671	\N	2025-08-03 11:10:09.671858	43	deck_submission
310	27	Video Upload	2	pending	{"document_types": ["video"], "required_videos": ["pitch", "product_demo"], "allows_documents": true}	\N	\N	2025-08-03 11:10:09.673317	44	video_upload
311	27	GP In-Person Interview	3	pending	{"interview_types": ["video_call", "in_person"], "requires_scheduling": true}	\N	\N	2025-08-03 11:10:09.674195	45	gp_interview
312	27	Founder Verification (KYC)	4	pending	{"document_types": ["identity", "background_check"], "requires_documents": true, "compliance_required": true}	\N	\N	2025-08-03 11:10:09.674953	46	kyc_verification
313	27	Due Diligence	5	pending	{"dd_categories": ["financial", "legal", "technical", "market"], "document_types": ["financial_report", "legal_docs", "market_analysis"], "allows_documents": true}	\N	\N	2025-08-03 11:10:09.675682	47	due_diligence
314	27	Term Sheet Negotiation / LOI	6	pending	{"document_types": ["term_sheet", "loi"], "allows_documents": true, "negotiation_rounds": true}	\N	\N	2025-08-03 11:10:09.676457	48	term_sheet
315	27	Publishing	7	pending	{"visibility": "investors", "marketing_materials": true}	\N	\N	2025-08-03 11:10:09.677215	49	publishing
316	27	Call for Commits / Investor Interaction	8	pending	{"commitment_tracking": true, "investor_management": true}	\N	\N	2025-08-03 11:10:09.677948	50	investor_commits
317	27	Commit Complete	9	pending	{"funding_target_check": true, "commitment_verification": true}	\N	\N	2025-08-03 11:10:09.678628	51	commit_complete
318	27	Signing - Vehicle	10	pending	{"legal_docs": true, "document_types": ["vehicle_agreement"], "signing_required": true}	\N	\N	2025-08-03 11:10:09.679351	52	signing_vehicle
319	27	Signing - Startup	11	pending	{"legal_docs": true, "document_types": ["startup_agreement"], "founder_signatures": true}	\N	\N	2025-08-03 11:10:09.680056	53	signing_startup
320	27	Funding Collection at Vehicle	12	pending	{"fund_verification": true, "payment_processing": true}	\N	\N	2025-08-03 11:10:09.680803	54	funding_collection
321	27	Funding Transfer to Startup	13	pending	{"compliance_checks": true, "transfer_verification": true}	\N	\N	2025-08-03 11:10:09.68152	55	funding_transfer
322	27	Round Closed	14	pending	{"final_reporting": true, "completion_verification": true}	\N	\N	2025-08-03 11:10:09.682267	56	round_closed
323	28	Deck Submission & Feedback	1	active	{"document_types": ["pitch_deck"], "allows_documents": true, "feedback_required": true}	\N	\N	2025-08-03 15:02:41.629105	43	deck_submission
324	28	Video Upload	2	pending	{"document_types": ["video"], "required_videos": ["pitch", "product_demo"], "allows_documents": true}	\N	\N	2025-08-03 15:02:41.629105	44	video_upload
325	28	GP In-Person Interview	3	pending	{"interview_types": ["video_call", "in_person"], "requires_scheduling": true}	\N	\N	2025-08-03 15:02:41.629105	45	gp_interview
326	28	Founder Verification (KYC)	4	pending	{"document_types": ["identity", "background_check"], "requires_documents": true, "compliance_required": true}	\N	\N	2025-08-03 15:02:41.629105	46	kyc_verification
327	28	Due Diligence	5	pending	{"dd_categories": ["financial", "legal", "technical", "market"], "document_types": ["financial_report", "legal_docs", "market_analysis"], "allows_documents": true}	\N	\N	2025-08-03 15:02:41.629105	47	due_diligence
328	28	Term Sheet Negotiation / LOI	6	pending	{"document_types": ["term_sheet", "loi"], "allows_documents": true, "negotiation_rounds": true}	\N	\N	2025-08-03 15:02:41.629105	48	term_sheet
329	28	Publishing	7	pending	{"visibility": "investors", "marketing_materials": true}	\N	\N	2025-08-03 15:02:41.629105	49	publishing
330	28	Call for Commits / Investor Interaction	8	pending	{"commitment_tracking": true, "investor_management": true}	\N	\N	2025-08-03 15:02:41.629105	50	investor_commits
331	28	Commit Complete	9	pending	{"funding_target_check": true, "commitment_verification": true}	\N	\N	2025-08-03 15:02:41.629105	51	commit_complete
332	28	Signing - Vehicle	10	pending	{"legal_docs": true, "document_types": ["vehicle_agreement"], "signing_required": true}	\N	\N	2025-08-03 15:02:41.629105	52	signing_vehicle
333	28	Signing - Startup	11	pending	{"legal_docs": true, "document_types": ["startup_agreement"], "founder_signatures": true}	\N	\N	2025-08-03 15:02:41.629105	53	signing_startup
334	28	Funding Collection at Vehicle	12	pending	{"fund_verification": true, "payment_processing": true}	\N	\N	2025-08-03 15:02:41.629105	54	funding_collection
335	28	Funding Transfer to Startup	13	pending	{"compliance_checks": true, "transfer_verification": true}	\N	\N	2025-08-03 15:02:41.629105	55	funding_transfer
336	28	Round Closed	14	pending	{"final_reporting": true, "completion_verification": true}	\N	\N	2025-08-03 15:02:41.629105	56	round_closed
337	29	Deck Submission & Feedback	1	active	{"document_types": ["pitch_deck"], "allows_documents": true, "feedback_required": true}	\N	\N	2025-08-03 18:13:55.147674	43	deck_submission
338	29	Video Upload	2	pending	{"document_types": ["video"], "required_videos": ["pitch", "product_demo"], "allows_documents": true}	\N	\N	2025-08-03 18:13:55.147674	44	video_upload
340	29	Founder Verification (KYC)	4	pending	{"document_types": ["identity", "background_check"], "requires_documents": true, "compliance_required": true}	\N	\N	2025-08-03 18:13:55.147674	46	kyc_verification
341	29	Due Diligence	5	pending	{"dd_categories": ["financial", "legal", "technical", "market"], "document_types": ["financial_report", "legal_docs", "market_analysis"], "allows_documents": true}	\N	\N	2025-08-03 18:13:55.147674	47	due_diligence
342	29	Term Sheet Negotiation / LOI	6	pending	{"document_types": ["term_sheet", "loi"], "allows_documents": true, "negotiation_rounds": true}	\N	\N	2025-08-03 18:13:55.147674	48	term_sheet
343	29	Publishing	7	pending	{"visibility": "investors", "marketing_materials": true}	\N	\N	2025-08-03 18:13:55.147674	49	publishing
344	29	Call for Commits / Investor Interaction	8	pending	{"commitment_tracking": true, "investor_management": true}	\N	\N	2025-08-03 18:13:55.147674	50	investor_commits
345	29	Commit Complete	9	pending	{"funding_target_check": true, "commitment_verification": true}	\N	\N	2025-08-03 18:13:55.147674	51	commit_complete
346	29	Signing - Vehicle	10	pending	{"legal_docs": true, "document_types": ["vehicle_agreement"], "signing_required": true}	\N	\N	2025-08-03 18:13:55.147674	52	signing_vehicle
347	29	Signing - Startup	11	pending	{"legal_docs": true, "document_types": ["startup_agreement"], "founder_signatures": true}	\N	\N	2025-08-03 18:13:55.147674	53	signing_startup
348	29	Funding Collection at Vehicle	12	pending	{"fund_verification": true, "payment_processing": true}	\N	\N	2025-08-03 18:13:55.147674	54	funding_collection
349	29	Funding Transfer to Startup	13	pending	{"compliance_checks": true, "transfer_verification": true}	\N	\N	2025-08-03 18:13:55.147674	55	funding_transfer
350	29	Round Closed	14	pending	{"final_reporting": true, "completion_verification": true}	\N	\N	2025-08-03 18:13:55.147674	56	round_closed
339	29	GP In-Person Interview	3	active	{"interview_types": ["video_call", "in_person"], "requires_scheduling": true, "completion_notes": "Let's schedule a call :)", "updated_by": "luisa@halbzeit.ai", "updated_at": "2025-08-05T08:19:33.123805"}	2025-08-05 08:19:33.116996	\N	2025-08-03 18:13:55.147674	45	gp_interview
\.


--
-- Data for Name: projects; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.projects (id, company_id, project_name, funding_round, current_stage_id, funding_sought, healthcare_sector_id, company_offering, project_metadata, tags, is_test, is_active, created_at, updated_at, owner_id) FROM stdin;
27	lilio	Lilio - Dojo Analysis	analysis	\N	Not specified\n\nThe visual analysis provided does not mention any specific funding amount that the startup is seeking. There are no phrases like 'seeking €X', 'raising $X', or similar in the descriptions of the slides. Therefore, based on the information given, it cannot be determined what specific funding amount is being sought by the startup.	\N	A wearable device that monitors infants' vital signs, such as heart rate and oxygen saturation, providing data to parents through a mobile app interface.	{"created_from_experiment": true, "experiment_id": 10, "experiment_name": "pipeline_1754218360807", "source_deck_id": 119, "created_by": "ramin@halbzeit.ai", "created_at": "2025-08-03T11:10:09.666583", "original_filename": "2025_Lilio Investment Deck.pdf", "classification": {"primary_sector": "diagnostics_devices", "secondary_sector": "Consumer Health & Wellness", "confidence_score": 0.95, "reasoning": "The company's offering \\u2013 a wearable device monitoring infant vital signs and providing data to parents via a mobile app \\u2013 directly aligns with the definition of Diagnostics & Medical Devices, specifically within the Wearable Health Monitors subcategory. The core business is providing a device for health monitoring, a key characteristic of this sector. The target market is parents of infants, and the solution is a physical device providing physiological data. While there's a mobile app component, the primary value proposition is the wearable device itself. The keyword analysis confirms the 'wearable' aspect. The focus is on providing diagnostic information, albeit in a consumer-facing manner.", "keywords_matched": ["wearable", "monitoring", "vital signs", "mobile app"], "classification_error": null}, "ai_extracted_company_name": "Lilio", "template_processing": null}	["dojo", "experiment", "ai-extracted", "diagnostics_devices"]	t	t	2025-08-03 11:10:09.666937	2025-08-03 11:10:09.666952	\N
28	international-testing-agency	test project	seed	\N	12	\N	\N	\N	\N	f	t	2025-08-03 15:02:41.638701	2025-08-03 15:02:41.638712	1
29	ismaning	ismaning - Initial Review	initial	\N	TBD	\N	It provides robotic surgical assistance through a multi-arm platform.	{"created_from_pitch_deck": true, "pitch_deck_id": 122, "original_filename": "LEM-Surgical-Opportunity-Overview.pdf", "auto_created": true, "created_at": "2025-08-03T18:13:55.170087", "classification": {"primary_sector": "consumer_health", "subcategory": "Health Optimization Tools", "confidence_score": 0.3, "reasoning": "Fallback classification - unable to access healthcare sectors from database", "secondary_sector": null, "keywords_matched": [], "recommended_template": null}}	\N	f	t	2025-08-03 18:13:55.170156	2025-08-03 18:13:55.170162	\N
\.


--
-- Data for Name: question_analysis_results; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.question_analysis_results (id, pitch_deck_id, question_id, raw_response, structured_response, score, confidence_score, processing_time, model_used, prompt_used, created_at) FROM stdin;
\.


--
-- Data for Name: questions; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.questions (id, review_id, question_text, asked_by, created_at) FROM stdin;
\.


--
-- Data for Name: reviews; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.reviews (id, pitch_deck_id, review_data, s3_review_url, status, created_at) FROM stdin;
\.


--
-- Data for Name: slide_feedback; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.slide_feedback (id, pitch_deck_id, slide_number, slide_filename, feedback_text, feedback_type, has_issues, created_at, updated_at) FROM stdin;
175	140	1	slide_1.jpg	The slide lacks context and doesn't immediately convey a business message; the abstract graphic feels purely aesthetic. The company name and date are too small and tucked away, diminishing their impact. Consider replacing the graphic with something more representative of the company's work or adding a short, clarifying tagline.	ai_analysis	t	2025-08-05 20:22:15.655264	2025-08-05 20:22:15.655267
180	140	6	slide_6.jpg	The slide is currently overwhelming and lacks clarity. Reduce the number of data points displayed and simplify the visuals; focus on the most impactful comparison (e.g., total availability vs. waiting list) to immediately convey the severity of the organ shortage. Consider a single, clear chart with larger font sizes and concise labels to improve readability and comprehension for investors.	ai_analysis	t	2025-08-05 20:22:21.027785	2025-08-05 20:22:21.027787
185	140	11	slide_11.jpg	The slide suffers from visual clutter and lacks a clear narrative. The truncated horizontal axis label and abundance of logos distract from the core data, and the connection between the data points and the listed applications isn't immediately obvious. Simplify the visual elements, clearly label the horizontal axis, and highlight the key takeaway regarding perfusion time and its benefits.	ai_analysis	t	2025-08-05 20:22:26.553819	2025-08-05 20:22:26.553823
136	138	3	slide_3.jpg	The slide suffers from a lack of visual hierarchy and relies too heavily on text, making it difficult to grasp quickly. Simplify the "moat" graphic – fewer concentric circles and more concise labels would improve readability. Explicitly label the chart axes and consider using fewer revenue categories for clarity and immediate understanding.	ai_analysis	t	2025-08-05 20:06:13.359369	2025-08-05 20:06:13.359372
137	138	4	slide_4.jpg	The slide is visually overwhelming and lacks clarity. The grid of photos with numerical labels is confusing and doesn't immediately convey a clear message; simplify the visual by focusing on a few key conditions or using a different visual representation. Prioritize clear messaging and reduce the text density to ensure investors quickly grasp the core value proposition of "The Phiggile."	ai_analysis	t	2025-08-05 20:06:14.539792	2025-08-05 20:06:14.539797
138	138	5	slide_5.jpg	The "To begin..." callout is confusing and disrupts the flow – remove it entirely. The slide needs a clearer indication of the percentages allocated to each category; just showing dollar amounts without context makes it difficult to grasp the investment priorities. Consider adding a brief sentence summarizing the overall strategy behind the fund allocation to improve understanding.	ai_analysis	t	2025-08-05 20:06:15.62448	2025-08-05 20:06:15.624484
151	139	2	slide_2.jpg	The slide lacks visual hierarchy and appears chaotic. The irregular icon placement and scattered data points make it difficult to quickly grasp the core message – simplify the layout and use a clear visual flow to guide the eye. Consider consolidating data and using a more structured design to improve readability and impact for investors.	ai_analysis	t	2025-08-05 20:13:06.166637	2025-08-05 20:13:06.166642
176	140	2	slide_2.jpg	The slide lacks crucial context; the connection between the labeled blocks and the bar graph isn't immediately clear. Simplify the labeled blocks – fewer categories and more descriptive labels would improve understanding. Finally, explicitly state the units on the bar graph’s axis to enhance data interpretability.	ai_analysis	t	2025-08-05 20:22:16.601441	2025-08-05 20:22:16.601443
181	140	7	slide_7.jpg	The slide suffers from overwhelming visual complexity; the schematic is too dense and lacks a clear focal point. Simplify the diagram significantly, highlighting only the *most* critical components and using callouts to explain their function. Prioritize readability by increasing font sizes and reducing the amount of text directly on the diagram itself.	ai_analysis	t	2025-08-05 20:22:22.03167	2025-08-05 20:22:22.031672
186	140	12	slide_12.jpg	The slide suffers from a lack of clear hierarchy and confusing terminology. The concentric circles, while visually interesting, don’t immediately convey the relationship between the values and labels – it's unclear what each circle *represents*. Simplify the labels to clearly articulate what each market segment encompasses and use a title to provide immediate context for investors.	ai_analysis	t	2025-08-05 20:22:27.632597	2025-08-05 20:22:27.6326
177	140	3	slide_3.jpg	The slide suffers from visual complexity; the color-coded markers and dense text create a cluttered feel, hindering quick comprehension. Simplify the timeline by reducing the number of markers and consolidating related achievements into fewer, clearer points. Prioritize readability by increasing font sizes and using more whitespace to guide the viewer's eye.	ai_analysis	t	2025-08-05 20:22:17.643085	2025-08-05 20:22:17.643088
182	140	8	slide_8.jpg	The slide suffers from a lack of visual hierarchy; the three graphs feel equally important, making it difficult to discern the core message. Simplify the slide by focusing on the most critical data point and consolidating the labels into a concise summary statement. Consider a more structured layout to guide the investor's eye and highlight the key takeaway.	ai_analysis	t	2025-08-05 20:22:23.115727	2025-08-05 20:22:23.11573
187	140	13	slide_13.jpg	The slide is overly complex and difficult to quickly grasp. Too many milestones crammed into each timeframe create visual clutter, and the technical jargon without immediate context will confuse investors. Simplify the timeline by grouping related milestones and providing brief explanations for the acronyms/technical terms.	ai_analysis	t	2025-08-05 20:22:28.573928	2025-08-05 20:22:28.57393
178	140	4	slide_4.jpg	The slide lacks visual hierarchy; all names and titles appear equally prominent, making it difficult to quickly identify key leadership roles. Consider highlighting the CEO and Chair with a slightly larger font or visual cue. While the background is aesthetically pleasing, it risks distracting from the team's credentials – simplify it or remove it entirely.	ai_analysis	t	2025-08-05 20:22:18.652954	2025-08-05 20:22:18.652956
183	140	9	slide_9.jpg	The slide needs simplification. The timeline graphic is visually dense and difficult to quickly interpret; consider highlighting only the Breakthrough Device designation and a key European approval date. Reduce the amount of specific text regarding regulatory bodies and dates – focus on the *significance* of the approvals (e.g., "FDA Breakthrough Device & European Regulatory Endorsement") to improve readability and investor comprehension.	ai_analysis	t	2025-08-05 20:22:24.413593	2025-08-05 20:22:24.413596
188	140	14	slide_14.jpg	The slide suffers from visual clutter; the pie chart’s color choices and segment sizes don't immediately convey clear distinctions in allocation. Reduce the number of segments in the pie chart or simplify the color palette to improve readability and highlight the most significant allocations. Consider integrating the milestone list into the pie chart explanation to streamline the information flow and avoid a disjointed feel.	ai_analysis	t	2025-08-05 20:22:29.758096	2025-08-05 20:22:29.758098
134	138	1	slide_1.jpg	The slide suffers from a lack of clear connection between the abstract graphic and the listed benefits. The graphic's purpose isn't immediately apparent, making it difficult to understand *how* it contributes to increased engagement, reach, etc. Consider adding a short caption explaining the graphic's representation or directly linking visual elements to the bullet points.	ai_analysis	t	2025-08-05 20:06:11.0172	2025-08-05 20:06:11.017202
135	138	2	slide_2.jpg	The slide is visually overwhelming and lacks a clear narrative; the sheer density of icons, photos, and text makes it impossible to grasp the core message quickly. Simplify the visual elements and prioritize a single, compelling takeaway – consider using fewer images and larger, more readable fonts. Establish a clear visual hierarchy to guide the investor's eye to the most important information.	ai_analysis	t	2025-08-05 20:06:12.261174	2025-08-05 20:06:12.261178
150	139	1	slide_1.jpg	The slide suffers from a severe lack of context; the droplet image, while aesthetically pleasing, doesn't immediately communicate anything about the business. Remove the droplet entirely and replace it with a concise headline explaining the slide's purpose (e.g., "Key Partnership Announcement" or "Customer Acquisition Growth"). The current layout prioritizes aesthetics over clarity, hindering investor comprehension.	ai_analysis	t	2025-08-05 20:13:05.160744	2025-08-05 20:13:05.160747
152	139	3	slide_3.jpg	The slide suffers from visual clutter and unclear hierarchy. The numerous icons and text blocks compete for attention, making it difficult to quickly grasp the core message; consolidate the icons into fewer, more impactful visuals and prioritize the "Integrating AI for Better Outcomes" tagline. Reduce the amount of text and focus on a single, compelling benefit for investors.	ai_analysis	t	2025-08-05 20:13:07.329313	2025-08-05 20:13:07.329316
153	139	4	slide_4.jpg	The slide lacks visual hierarchy; the mockup dominates, making the "Obert Advantage" bullet points feel secondary. Simplify the mockup to focus attention on the key features and consider a more concise list – too much text overwhelms the viewer. Prioritize showcasing *how* the AI and personalization benefit the user, not just stating the features.	ai_analysis	t	2025-08-05 20:13:08.439451	2025-08-05 20:13:08.439453
154	139	5	slide_5.jpg	The slide suffers from visual clutter and text density, making it difficult to grasp the key takeaway quickly. Simplify the design by removing the concentric circles and presenting the market sizes as clear, labeled figures with a concise explanation of how they were derived. Prioritize the SOM and 2030 projection to highlight the achievable market opportunity.	ai_analysis	t	2025-08-05 20:13:09.570713	2025-08-05 20:13:09.570718
155	139	6	slide_6.jpg	The slide suffers from text readability issues – bullet points are likely too small and dense for quick understanding. Simplify the messaging in each section, focusing on one key takeaway per area, and consider a more impactful visual representation of the user growth chart (e.g., a line graph emphasizing the growth rate). Prioritize clarity and conciseness to ensure investors grasp the business model quickly.	ai_analysis	t	2025-08-05 20:13:10.877814	2025-08-05 20:13:10.877817
156	139	7	slide_7.jpg	The slide suffers from visual clutter due to the layered graph and numerous annotations; simplify the graph to highlight only the most probable scenario and key data points. Reduce text density by removing unnecessary annotations and consider a larger font size for improved readability. This will allow investors to quickly grasp the projected growth trajectory and understand the core business case.	ai_analysis	t	2025-08-05 20:13:11.982614	2025-08-05 20:13:11.982618
157	139	8	slide_8.jpg	The slide suffers from a lack of visual hierarchy; the reliance on icons without sufficient context makes it difficult to grasp the strategy quickly. Reduce the number of icons and accompanying phrases to focus on the 3-4 most impactful channels, and briefly explain *why* these were chosen. This will improve comprehension and make the slide more digestible for investors.	ai_analysis	t	2025-08-05 20:13:13.18057	2025-08-05 20:13:13.180572
158	139	9	slide_9.jpg	The slide suffers from visual complexity and lacks clear context. The radial design, while potentially interesting, is overwhelming with numerous competitors and the green-to-red gradient is meaningless without explanation. Simplify the number of competitors shown and explicitly define what the color gradient represents to improve comprehension.	ai_analysis	t	2025-08-05 20:13:14.169247	2025-08-05 20:13:14.169251
159	139	10	slide_10.jpg	This slide is overwhelmingly dense and difficult to digest quickly. Prioritize the 2-3 most impactful metrics (likely revenue growth and user stickiness) and present them prominently; the rest should be supporting data in an appendix or omitted entirely. Simplify the visual representations to enhance readability and avoid overwhelming the investor.	ai_analysis	t	2025-08-05 20:13:15.236411	2025-08-05 20:13:15.236415
160	139	11	slide_11.jpg	The slide suffers from visual complexity due to the sheer number of portraits; it's difficult to process quickly. Prioritize showcasing only the *most* critical leadership and advisory members to improve readability and focus on key expertise. Consider a brief, overarching statement at the top summarizing the value of this experienced team.	ai_analysis	t	2025-08-05 20:13:16.262551	2025-08-05 20:13:16.262554
161	139	12	slide_12.jpg	The slide suffers from visual complexity due to the dense text labels alongside the pie chart segments, making it hard to quickly grasp the distribution. Prioritize readability by simplifying the labels (perhaps using icons or fewer words) and consider reordering the segments to highlight the most significant allocations. Finally, the "Discount 18-month" category is confusing and needs clarification or removal.	ai_analysis	t	2025-08-05 20:13:17.493402	2025-08-05 20:13:17.493405
162	139	13	slide_13.jpg	This slide is a significant problem. The overwhelming number of URLs and social media handles clutters the visual and detracts from the core message. Simplify the design by removing extraneous URLs and focusing on the app's core value proposition, rather than a list of links.\n\n\n\nSLIDE_NOT_OK	ai_analysis	t	2025-08-05 20:13:18.575509	2025-08-05 20:13:18.575511
163	139	14	slide_14.jpg	The slide lacks visual hierarchy and feels disjointed. The large numbers are attention-grabbing, but without clear context, their significance isn't immediately apparent – investors will need more than just "Rewards" to understand *what* is being rewarded and *why* these numbers matter. Consider adding a concise title explaining the metric being measured (e.g., "Key Behavioral Improvements") and a brief explanation of how DynamiCare Health achieves these results.	ai_analysis	t	2025-08-05 20:13:19.999804	2025-08-05 20:13:19.999808
179	140	5	slide_5.jpg	The slide suffers from visual clutter due to the dense grid of photos and the unclear bar graph; reduce the number of photos or increase their size for better readability. The unlabeled y-axis on the bar graph renders it meaningless and should be removed or clarified. Prioritize readability and simplify the layout to highlight the "60+ years experience" – this is likely the key takeaway for investors.	ai_analysis	t	2025-08-05 20:22:19.894014	2025-08-05 20:22:19.894015
184	140	10	slide_10.jpg	The slide suffers from visual complexity due to the combination of a timeline and bar graph, potentially overwhelming the viewer. Reduce the amount of text on the timeline and consider simplifying the bar graph to highlight only the most critical financial projections. Prioritize visual hierarchy by ensuring key data points are immediately apparent, potentially through animation or larger font sizes.	ai_analysis	t	2025-08-05 20:22:25.4788	2025-08-05 20:22:25.478802
189	140	15	slide_15.jpg	This is essentially a contact details slide.\n\n**Feedback:**\n\nThe slide is functionally clear, but lacks context – why is this information being presented? Reduce the number of logos and consider a brief title like "Contact Information" or "Location & Contact" to immediately signal the slide’s purpose. Prioritize readability by ensuring sufficient contrast between text and background.	ai_analysis	t	2025-08-05 20:22:30.952514	2025-08-05 20:22:30.952516
\.


--
-- Data for Name: specialized_analysis_results; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.specialized_analysis_results (id, pitch_deck_id, analysis_type, analysis_result, structured_result, confidence_score, model_used, processing_time, created_at) FROM stdin;
\.


--
-- Data for Name: stage_templates; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.stage_templates (id, stage_name, stage_code, description, stage_order, is_required, estimated_duration_days, stage_metadata, is_active, created_at, updated_at) FROM stdin;
43	Deck Submission & Feedback	deck_submission	Initial pitch deck upload and GP review with feedback	1	t	7	{"document_types": ["pitch_deck"], "allows_documents": true, "feedback_required": true}	t	\N	\N
44	Video Upload	video_upload	Upload pitch video and product demonstration video	2	t	3	{"document_types": ["video"], "required_videos": ["pitch", "product_demo"], "allows_documents": true}	t	\N	\N
45	GP In-Person Interview	gp_interview	Face-to-face or video interview with General Partners	3	t	5	{"interview_types": ["video_call", "in_person"], "requires_scheduling": true}	t	\N	\N
46	Founder Verification (KYC)	kyc_verification	Know Your Customer verification and founder background checks	4	t	7	{"document_types": ["identity", "background_check"], "requires_documents": true, "compliance_required": true}	t	\N	\N
47	Due Diligence	due_diligence	Comprehensive analysis of business, financials, market, and legal aspects	5	t	21	{"dd_categories": ["financial", "legal", "technical", "market"], "document_types": ["financial_report", "legal_docs", "market_analysis"], "allows_documents": true}	t	\N	\N
48	Term Sheet Negotiation / LOI	term_sheet	Negotiate terms and sign Letter of Intent	6	t	14	{"document_types": ["term_sheet", "loi"], "allows_documents": true, "negotiation_rounds": true}	t	\N	\N
49	Publishing	publishing	Publish investment opportunity to investor network	7	t	2	{"visibility": "investors", "marketing_materials": true}	t	\N	\N
50	Call for Commits / Investor Interaction	investor_commits	Collect investor commitments and manage investor communications	8	t	30	{"commitment_tracking": true, "investor_management": true}	t	\N	\N
51	Commit Complete	commit_complete	All required commitments secured and verified	9	t	7	{"funding_target_check": true, "commitment_verification": true}	t	\N	\N
52	Signing - Vehicle	signing_vehicle	Legal documentation signing for investment vehicle	10	t	5	{"legal_docs": true, "document_types": ["vehicle_agreement"], "signing_required": true}	t	\N	\N
53	Signing - Startup	signing_startup	Legal documentation signing by startup founders	11	t	5	{"legal_docs": true, "document_types": ["startup_agreement"], "founder_signatures": true}	t	\N	\N
54	Funding Collection at Vehicle	funding_collection	Collect committed funds into investment vehicle	12	t	10	{"fund_verification": true, "payment_processing": true}	t	\N	\N
55	Funding Transfer to Startup	funding_transfer	Transfer funds from vehicle to startup account	13	t	3	{"compliance_checks": true, "transfer_verification": true}	t	\N	\N
56	Round Closed	round_closed	Investment round successfully completed	14	t	1	{"final_reporting": true, "completion_verification": true}	t	\N	\N
\.


--
-- Data for Name: startup_classifications; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.startup_classifications (id, pitch_deck_id, company_offering, primary_sector_id, subcategory, confidence_score, classification_reasoning, secondary_sector_id, keywords_matched, template_used, manual_override, manual_override_reason, classified_by, created_at) FROM stdin;
\.


--
-- Data for Name: task_dependencies; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.task_dependencies (id, dependent_task_id, depends_on_task_id, dependency_type, created_at) FROM stdin;
\.


--
-- Data for Name: template_chapters; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.template_chapters (id, template_id, chapter_id, name, description, weight, order_index, is_required, enabled, chapter_prompt_template, scoring_prompt_template, created_at, modified_at, analysis_template_id) FROM stdin;
1	9	problem_analysis	Problem Analysis	Analysis of the problem being addressed by the startup	1.0	1	t	t	\N	\N	\N	\N	\N
2	9	solution_approach	Solution Approach	Analysis of the proposed solution and competitive differentiation	1.0	2	t	t	\N	\N	\N	\N	\N
3	9	product_market_fit	Product Market Fit	Customer validation and market adoption analysis	1.0	3	t	t	\N	\N	\N	\N	\N
4	9	monetization	Monetization	Revenue model and pricing strategy analysis	1.0	4	t	t	\N	\N	\N	\N	\N
5	9	financials	Financials	Financial metrics and funding requirements analysis	1.0	5	t	t	\N	\N	\N	\N	\N
6	9	use_of_funds	Use of Funds	Investment strategy and future plans analysis	1.0	6	t	t	\N	\N	\N	\N	\N
7	9	organization	Organization	Team, experience, and organizational maturity analysis	1.0	7	t	t	\N	\N	\N	\N	\N
8	5	chapter_1	New Chapter1		1.0	0	t	t	\N	\N	\N	\N	\N
\.


--
-- Data for Name: template_configurations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.template_configurations (id, user_id, use_single_template, selected_template_id, created_at, updated_at) FROM stdin;
1	1	f	\N	2025-08-06 07:15:32.45516	2025-08-06 07:15:32.45516
\.


--
-- Data for Name: template_performance; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.template_performance (id, template_id, pitch_deck_id, total_processing_time, successful_questions, failed_questions, average_confidence, gp_rating, gp_feedback, created_at) FROM stdin;
\.


--
-- Data for Name: test_projects; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.test_projects (id, company_id, project_name, funding_round, current_stage_id, funding_sought, healthcare_sector_id, company_offering, project_metadata, is_active, created_at, updated_at, tags, is_test) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.users (id, email, password_hash, company_name, role, preferred_language, is_verified, verification_token, verification_token_expires, created_at, last_login, first_name, last_name, must_change_password) FROM stdin;
1	ramin@halbzeit.ai	$2b$12$hzEH1iGVYwMDeCy/UiG1A.tvEUjingo34hByKNyZkCi4c9kFwrSmm	HALBZEIT	gp	en	t	\N	\N	2025-07-13 08:39:59.796468	2025-08-06 08:04:57.098953	\N	\N	f
23	ramin.assadollahi@exb.de	$2b$12$wzJOC9ihFeyvG.IrGb9KwukAFaHQ7J6anAorudD9rWRxvZILTmvTq	Ramin ExB	gp	de	t	\N	\N	2025-08-05 07:04:15.059514	2025-08-05 07:05:35.473891	Ramin	ExB	f
24	luisa@halbzeit.ai	$2b$12$h9aWgl.EYweMM.0D9d26iOSRqx1/j2Sx3ZJ2LGcfKoUl.CJAz1IO.	Luisa Wasilewski	gp	en	t	\N	\N	2025-08-05 08:14:09.196247	2025-08-05 08:17:26.495781	Luisa	Wasilewski	f
12	ramin@assadollahi.de	$2b$12$QQL6Y4hE4k9BwW6zz6AgiOS5pW56bwL6/i3.fTLdmHmnHo1QXvz/.	ismaning	startup	en	t	\N	\N	2025-07-17 10:36:53.943018	2025-08-06 12:20:20.938868	Ramin	Assadollahi	f
\.


--
-- Data for Name: visual_analysis_cache; Type: TABLE DATA; Schema: public; Owner: review_user
--

COPY public.visual_analysis_cache (id, pitch_deck_id, analysis_result_json, vision_model_used, prompt_used, created_at) FROM stdin;
72	119	{"visual_analysis_results": [{"company_id": "dojo", "deck_id": 119, "deck_name": "4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck", "description": "Here is a description of the slide, framed from an investor's perspective:\\n\\nThe slide presents a screen capture of a mobile device displaying what appears to be a user interface. The dominant visual element is an image of a child, rendered in a muted, soft-focus style. Overlaying this image is a visual representation of a wearable device positioned on the child\\u2019s wrist. \\n\\nSeveral textual elements are visible on the screen capture. Text labels such as \\u201cNoah\\u201d, \\u201cAktuelle Werte\\u201d, \\u201c75\\u201d, and \\u201cBasistemperatur\\u201d are presented, along with a glyph indicating a heart rate measurement. Further textual identifiers such as \\"Band\\" and \\"Sauerstoff\\" are also displayed.\\n\\nBelow the main image, a simplified graphical representation is evident, depicted as a series of ascending and descending bars. A numerical value, \\u201c97\\u201d, is visible in close proximity to this graphical element. \\n\\nThe slide's aesthetic appears purposefully minimalist, suggesting a focus on design and user experience. It appears the company is attempting to convey ease of use and integration with daily routines.", "page_number": 1, "slide_image_path": "analysis/4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck/slide_1.jpg"}, {"company_id": "dojo", "deck_id": 119, "deck_name": "4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck", "description": "Here's a formal description of the slide from an investor's perspective:\\n\\nThe slide presents a visually dominated design featuring a full-frame photographic image. The image depicts a young child, appearing to be an infant, positioned supine within a sleep environment. The lighting is subdued, highlighting the subject's features and creating a soft, muted atmosphere. \\n\\nSuperimposed over the central image, positioned centrally and vertically along the image, is the text \\"Sleep\\". Further positioned in the top right corner of the image, in smaller text, is the name \\"lilio\\".\\n\\nThe slide\\u2019s overall aesthetic aims for a minimalist and emotionally resonant presentation. The prominence of the visual element suggests a focus on the user experience and the emotional aspect of the product or service being presented.", "page_number": 2, "slide_image_path": "analysis/4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck/slide_2.jpg"}, {"company_id": "dojo", "deck_id": 119, "deck_name": "4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck", "description": "Here's a description of the slide from an investor's perspective:\\n\\nThe slide presents a visual representation of a product interface, likely a mobile application, displaying data related to infant monitoring. The layout appears clean and intuitive, utilizing a minimalist aesthetic. \\n\\nThe central visual element features a depiction of a wearable device, seemingly a band or clip, presumably worn by an infant. Adjacent to this is an image of a separate device, potentially a base station or receiver, appearing to communicate with the wearable. \\n\\nOverlaid on the mobile device screen are several text elements and data indicators. The text \\u201cAktuelle Werte\\u201d is visible, suggesting a section displaying current readings. Numerical data, presented in a clear, legible format, indicates values labeled as \\"75\\u00b0C\\" and \\"97%\\". Further text displays \\u201cBasisstation\\u201d. \\n\\nThe interface utilizes a graphic element, potentially a gauge or progress bar, demonstrating a value labelled \\"97.\\" It appears to be a visual representation of a measurement that\\u2019s close to the maximum recorded amount.", "page_number": 3, "slide_image_path": "analysis/4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck/slide_3.jpg"}, {"company_id": "dojo", "deck_id": 119, "deck_name": "4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck", "description": "Here's a description of the slide from an investor's perspective:\\n\\nThe slide presents a visual composition utilizing a pastel color palette, predominantly featuring shades of blue and yellow. The central element is a photograph depicting a mother and infant in an intimate, close-up embrace. The composition emphasizes the physical closeness and appears to depict an emotional connection between the individuals.\\n\\nBeneath the image, a series of keywords are presented in a vertical list, arranged in a stylized font. The list consists of terms including, \\u201cCalm & Safe,\\u201d \\u201cEmpowered & Confident,\\u201d \\u201cReliable,\\u201d \\u201cHolistic,\\u201d and \\u201cConnected.\\u201d These keywords are seemingly intended to convey the overall theme or benefits associated with the product or service being presented.\\n\\nThere is no indication of quantitative data displayed.", "page_number": 4, "slide_image_path": "analysis/4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck/slide_4.jpg"}, {"company_id": "dojo", "deck_id": 119, "deck_name": "4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck", "description": "Here's a description of the slide from an investor's perspective:\\n\\nThe slide presents a full-frame photograph depicting a young child seated in what appears to be a carrier or sling worn by an adult, presumably a parent. The child is facing forward, appearing engaged, while the adult\\u2019s face is partially obscured. The overall aesthetic is clean and minimalist. \\n\\nText overlays are minimal. Along the top left corner, the phrase \\"Made for Every Moment\\" is displayed in a relatively small font. The bottom right corner contains the brand name \\"Lilio\\" in a stylized typeface.\\n\\nThe image evokes a feeling of ease and connection, suggesting the product is designed for seamless integration into everyday life. The photograph\\u2019s composition and lighting contribute to a sense of warmth and approachability.", "page_number": 5, "slide_image_path": "analysis/4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck/slide_5.jpg"}, {"company_id": "dojo", "deck_id": 119, "deck_name": "4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck", "description": "Here's a description of the slide from an investor's perspective:\\n\\nThe slide presents a visually clean and minimalist aesthetic, dominated by a photograph of a baby's hand gently grasping an adult's finger. The background is a soft, muted grey, and the overall impression is one of care and connection. \\n\\nSuperimposed on the lower right-hand corner of the image is a vertically oriented text block. The heading reads \\"Introducing\\" in a larger font size, followed by \\"Pioneering\\" in a slightly smaller font. Below that, the words \\"Baby\\" and \\"Monitoring\\" are presented together in a larger font size. Further down in smaller text are the words, \\"A state-of-the-art\\", followed by \\"Solution\\" and followed by the number \\"7.\\"\\n\\nWithin the lower left-hand corner are five icons stacked vertically. Each is labelled with text below it; \\"Oxygen Saturation,\\" \\"Heart Rate,\\" \\"Comfort\\", \\"Diaries\\" and \\"Audio.\\"\\n\\nThe slide employs a modern and sophisticated design, aiming to convey the brand's approach to baby monitoring in a reassuring manner.", "page_number": 6, "slide_image_path": "analysis/4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck/slide_6.jpg"}, {"company_id": "dojo", "deck_id": 119, "deck_name": "4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck", "description": "Here's a description of the slide from an investor's perspective:\\n\\nThe slide presents a competitive landscape analysis, showcasing three distinct products within the infant monitoring market. Each product is represented visually with an image depicting its form factor \\u2013 a sock, a bracelet, and another bracelet. \\n\\nBelow each image, a product name is clearly displayed: \\u201cOwlet Smart Sock,\\u201d \\u201cNeeBo Sensor Bracelet,\\u201d and \\"Lilio Bracelet.\\" \\n\\nA heading at the top of the slide states \\"Competitors\\" in a prominent font. \\n\\nBeneath each product's name, a short textual description is visible. For the Owlet Smart Sock, it states \\u201cproducts are designed for sudden infant alerting.\\u201d For the NeeBo Sensor Bracelet, the description reads \\u201cthe smallest and most comfortable bracelet.\\u201d Lastly, the Lilio Bracelet is described as \\u201cPatent-pending technology\\u201d.\\n\\nThe layout appears intended to facilitate a visual comparison of available solutions, highlighting each competitor\\u2019s product characteristics.", "page_number": 7, "slide_image_path": "analysis/4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck/slide_7.jpg"}, {"company_id": "dojo", "deck_id": 119, "deck_name": "4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck", "description": "Here's a formal description of the slide from an investor's perspective:\\n\\nThe slide presents a comparative financial projection for a product offering, seemingly a wearable device with associated services. It appears to be structured to contrast a baseline scenario (\\"Basic\\") with a premium offering (\\"Premium\\"). The slide is divided into distinct sections representing different revenue streams: \\"Hardware,\\" \\"Basic App,\\" and \\"Subscription.\\"\\n\\nThe revenue projections for each category are presented for the years 2024 and 2026. The values are shown in Euros (\\u20ac). For the \\"Hardware\\" category, the projections indicate \\u20ac75 million in 2024, escalating to \\u20ac97 million by 2026. Similarly, the \\"Basic App\\" revenue is projected to increase from \\u20ac75 million in 2024 to \\u20ac97 million in 2026. \\"Subscription\\" revenue demonstrates a significant increase, with a projection of \\u20ac399 million in 2024, increasing to \\u20ac843 million by 2026.\\n\\nThe visual presentation includes clearly defined labels for the revenue streams and projected years. The numerical values are prominently displayed, suggesting an emphasis on quantitative performance. A small logo, identified as \\"Lilio,\\" is visible in the upper right corner.", "page_number": 8, "slide_image_path": "analysis/4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck/slide_8.jpg"}, {"company_id": "dojo", "deck_id": 119, "deck_name": "4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck", "description": "Here's a description of the slide from an investor's perspective, focusing on observations without interpretation of the content:\\n\\nThe slide appears to be visually complex, incorporating numerous textual elements arranged in a clustered, layered format. The slide's presentation style prioritizes a dense aggregation of keywords and phrases rather than a structured narrative flow.\\n\\nThe textual content demonstrates a focus on digital marketing strategies and consumer engagement. Terms related to e-commerce, including \\"EINZELHANDEL\\" and \\"D2C\\" are prominently featured. Further terms suggest an emphasis on data analysis, customer feedback, and targeted audience acquisition.\\n\\nSeveral phrases within the text appear to delineate distinct areas of focus, such as \\"Community Aufbau\\" and \\"Social Proof.\\" The arrangement of these phrases, along with the keywords associated with them, implies a multifaceted approach to marketing and customer relationship management.\\n\\nSeveral categories or areas of focus are demarcated by headings such as \\"EINZELHANDEL\\", \\"Wachstumsstrategie\\", \\"Social Media\\" and \\"Pr\\u00e4senz.\\" These sections indicate a segmented approach to the overall marketing and business plan.\\n\\nWhile the slide predominantly contains textual information, there are indications of potential data visualization through the use of numerous phrases and keywords related to performance metrics. The presence of expressions related to data analysis and audience targeting suggests there are potentially charts or graphs illustrating customer behavior or market trends, although their exact nature is not discernible from the presented image. These visualizations are likely intended to support the claims made within the associated text.", "page_number": 9, "slide_image_path": "analysis/4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck/slide_9.jpg"}, {"company_id": "dojo", "deck_id": 119, "deck_name": "4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck", "description": "Here's a formal description of the slide from an investor's perspective:\\n\\nThe slide presents a visual layout divided into distinct sections, appearing to outline a staged approach or timeline. The top portion features text, indicating a progression from \\"Wellness\\" to \\"Data Owners\\" and concludes with \\"Monitoring to Healthcare Revolution.\\" It suggests a journey or evolution, with \\"Wellness\\" serving as an initial point and \\"Healthcare Revolution\\" representing a desired outcome.\\n\\nBeneath the textual header, a graphic occupies a significant portion of the slide. The graphic is structured as a series of connected circles or nodes. Each node displays textual information. The nodes are visually linked, indicating a sequential or interconnected process. A series of numerical values are displayed on the side of the nodes, indicating specific milestones or timelines within the process. \\n\\nThe presentation style employs a clean aesthetic, utilizing a muted color palette with a clear emphasis on textual information. Overall, the slide appears to be intended to communicate a staged process or strategic roadmap, likely pertaining to a shift in healthcare delivery or technological adoption.", "page_number": 10, "slide_image_path": "analysis/4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck/slide_10.jpg"}, {"company_id": "dojo", "deck_id": 119, "deck_name": "4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck", "description": "Here's a description of the slide from an investor's perspective:\\n\\nThe slide presents market sizing data, segmented into three categories: Total Addressable Market (TAM), Serviceable Available Market (SAM), and Serviceable Obtainable Market (SOM). Each category is accompanied by an associated numerical value expressed in currency units, along with a descriptive text label underneath the value.\\n\\nThe presentation employs a horizontal bar graph to visually represent the relative magnitudes of each market segment. The bar representing the TAM is significantly larger than the bar representing the SOM, indicating a considerable difference in the overall potential versus the achievable market size within a given timeframe or scope. The SAM bar occupies an intermediate position between the TAM and SOM bars. \\n\\nBeneath each market segment, additional text provides a detail regarding consumer adoption, with percentages and units of measurement. A footer at the bottom of the slide includes a timestamp and a reference number.", "page_number": 11, "slide_image_path": "analysis/4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck/slide_11.jpg"}, {"company_id": "dojo", "deck_id": 119, "deck_name": "4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck", "description": "Here's a description of the slide from an investor's perspective:\\n\\nThis slide appears to be dedicated to showcasing the company's advisory board and key backers. It's densely populated with individual portraits, suggesting a significant number of influential supporters. Each portrait is accompanied by a name and title, indicating the professional standing and role of each individual or entity. \\n\\nThe presentation of the advisory board appears to be hierarchical; the individuals are organized in rows, likely sorted by perceived importance or contribution. There are clearly defined sections labeled \\u201cAdvisors\\u201d and \\u201cBackers.\\u201d \\n\\nSeveral logos of institutions and companies are displayed beneath the names and titles, representing organizations that have provided support or are associated with the listed individuals. These logos are positioned in a manner that denotes partnership or association. \\n\\nThere are several text labels at the bottom of the slide, appearing to be an ongoing list, as they are cut off and have the text \\"and further.\\" This suggests a comprehensive list that extends beyond what is visibly presented.", "page_number": 12, "slide_image_path": "analysis/4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck/slide_12.jpg"}, {"company_id": "dojo", "deck_id": 119, "deck_name": "4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck", "description": "Here's a description of the slide, tailored for an investor's perspective:\\n\\nThe slide presents a visually minimalist aesthetic. The primary imagery features a close-up photograph of an infant, positioned centrally within the frame. The photograph occupies the majority of the slide's area, suggesting a focus on the target demographic. The infant appears to be resting comfortably against a light-colored surface, possibly a blanket or crib bedding. \\n\\nAccompanying the image are textual elements situated within the lower right-hand corner of the slide. A title \\"Dr. Nadine Wunderlich\\" is present above a subsequent line identifying her role as \\"Founder\\". This information is immediately followed by a contact designation \\"lilio@nadine.wunderlich.de\\" and a telephone number \\"+49 176 244 56\\". \\n\\nThe overall presentation conveys a sense of simplicity and potential focus on a consumer-facing product or service catering to young children or their caregivers.", "page_number": 13, "slide_image_path": "analysis/4815c2d5e4544c7d85db5b778a586d26_2025_Lilio Investment Deck/slide_13.jpg"}]}	gemma3:12b	Describe this slide from a pitchdeck from a perspective of an investor, but do not interpret the content. Make sure to include anything notable about it, include text you see in the image, if you see any charts or graphs, describe them in a way that a person that doesn't see them would understand the content. Your style should be rather formal, not colloquial. Do not include any conversational text such as "Okay, here's a detailed description of the image, focusing on the requested aspects:"	2025-08-03 10:43:10.88769
\.


--
-- Name: analysis_templates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.analysis_templates_id_seq', 9, true);


--
-- Name: answers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.answers_id_seq', 1, false);


--
-- Name: chapter_analysis_results_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.chapter_analysis_results_id_seq', 1, false);


--
-- Name: chapter_questions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.chapter_questions_id_seq', 29, true);


--
-- Name: classification_performance_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.classification_performance_id_seq', 1, false);


--
-- Name: extraction_experiments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.extraction_experiments_id_seq', 10, true);


--
-- Name: gp_template_customizations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.gp_template_customizations_id_seq', 1, false);


--
-- Name: healthcare_sectors_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.healthcare_sectors_id_seq', 8, true);


--
-- Name: healthcare_templates_deprecated_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.healthcare_templates_deprecated_id_seq', 1, false);


--
-- Name: model_configs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.model_configs_id_seq', 4, true);


--
-- Name: pipeline_prompts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.pipeline_prompts_id_seq', 19, true);


--
-- Name: pitch_decks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.pitch_decks_id_seq', 144, true);


--
-- Name: processing_progress_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.processing_progress_id_seq', 5668, true);


--
-- Name: processing_queue_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.processing_queue_id_seq', 24, true);


--
-- Name: production_projects_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.production_projects_id_seq', 1, false);


--
-- Name: project_documents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.project_documents_id_seq', 68, true);


--
-- Name: project_interactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.project_interactions_id_seq', 1, false);


--
-- Name: project_invitations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.project_invitations_id_seq', 1, true);


--
-- Name: project_members_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.project_members_id_seq', 1, true);


--
-- Name: project_stages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.project_stages_id_seq', 350, true);


--
-- Name: projects_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.projects_id_seq', 29, true);


--
-- Name: question_analysis_results_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.question_analysis_results_id_seq', 1, false);


--
-- Name: questions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.questions_id_seq', 1, false);


--
-- Name: reviews_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.reviews_id_seq', 1, false);


--
-- Name: slide_feedback_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.slide_feedback_id_seq', 225, true);


--
-- Name: specialized_analysis_results_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.specialized_analysis_results_id_seq', 1, false);


--
-- Name: stage_templates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.stage_templates_id_seq', 56, true);


--
-- Name: startup_classifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.startup_classifications_id_seq', 1, false);


--
-- Name: task_dependencies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.task_dependencies_id_seq', 1, false);


--
-- Name: template_chapters_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.template_chapters_id_seq', 8, true);


--
-- Name: template_configurations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.template_configurations_id_seq', 1, true);


--
-- Name: template_performance_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.template_performance_id_seq', 1, false);


--
-- Name: test_projects_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.test_projects_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.users_id_seq', 24, true);


--
-- Name: visual_analysis_cache_id_seq; Type: SEQUENCE SET; Schema: public; Owner: review_user
--

SELECT pg_catalog.setval('public.visual_analysis_cache_id_seq', 73, true);


--
-- Name: analysis_templates analysis_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.analysis_templates
    ADD CONSTRAINT analysis_templates_pkey PRIMARY KEY (id);


--
-- Name: answers answers_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.answers
    ADD CONSTRAINT answers_pkey PRIMARY KEY (id);


--
-- Name: chapter_analysis_results chapter_analysis_results_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.chapter_analysis_results
    ADD CONSTRAINT chapter_analysis_results_pkey PRIMARY KEY (id);


--
-- Name: chapter_questions chapter_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.chapter_questions
    ADD CONSTRAINT chapter_questions_pkey PRIMARY KEY (id);


--
-- Name: classification_performance classification_performance_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.classification_performance
    ADD CONSTRAINT classification_performance_pkey PRIMARY KEY (id);


--
-- Name: extraction_experiments extraction_experiments_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.extraction_experiments
    ADD CONSTRAINT extraction_experiments_pkey PRIMARY KEY (id);


--
-- Name: gp_template_customizations gp_template_customizations_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.gp_template_customizations
    ADD CONSTRAINT gp_template_customizations_pkey PRIMARY KEY (id);


--
-- Name: healthcare_sectors healthcare_sectors_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.healthcare_sectors
    ADD CONSTRAINT healthcare_sectors_pkey PRIMARY KEY (id);


--
-- Name: healthcare_templates_deprecated healthcare_templates_deprecated_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.healthcare_templates_deprecated
    ADD CONSTRAINT healthcare_templates_deprecated_pkey PRIMARY KEY (id);


--
-- Name: model_configs model_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.model_configs
    ADD CONSTRAINT model_configs_pkey PRIMARY KEY (id);


--
-- Name: pipeline_prompts pipeline_prompts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pipeline_prompts
    ADD CONSTRAINT pipeline_prompts_pkey PRIMARY KEY (id);


--
-- Name: pitch_decks pitch_decks_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.pitch_decks
    ADD CONSTRAINT pitch_decks_pkey PRIMARY KEY (id);


--
-- Name: processing_progress processing_progress_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.processing_progress
    ADD CONSTRAINT processing_progress_pkey PRIMARY KEY (id);


--
-- Name: processing_queue processing_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.processing_queue
    ADD CONSTRAINT processing_queue_pkey PRIMARY KEY (id);


--
-- Name: processing_servers processing_servers_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.processing_servers
    ADD CONSTRAINT processing_servers_pkey PRIMARY KEY (id);


--
-- Name: production_projects production_projects_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.production_projects
    ADD CONSTRAINT production_projects_pkey PRIMARY KEY (id);


--
-- Name: project_documents project_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.project_documents
    ADD CONSTRAINT project_documents_pkey PRIMARY KEY (id);


--
-- Name: project_interactions project_interactions_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.project_interactions
    ADD CONSTRAINT project_interactions_pkey PRIMARY KEY (id);


--
-- Name: project_invitations project_invitations_invitation_token_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_invitations
    ADD CONSTRAINT project_invitations_invitation_token_key UNIQUE (invitation_token);


--
-- Name: project_invitations project_invitations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_invitations
    ADD CONSTRAINT project_invitations_pkey PRIMARY KEY (id);


--
-- Name: project_invitations project_invitations_project_id_email_status_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_invitations
    ADD CONSTRAINT project_invitations_project_id_email_status_key UNIQUE (project_id, email, status);


--
-- Name: project_members project_members_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_members
    ADD CONSTRAINT project_members_pkey PRIMARY KEY (id);


--
-- Name: project_members project_members_project_id_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_members
    ADD CONSTRAINT project_members_project_id_user_id_key UNIQUE (project_id, user_id);


--
-- Name: project_stages project_stages_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.project_stages
    ADD CONSTRAINT project_stages_pkey PRIMARY KEY (id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: question_analysis_results question_analysis_results_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.question_analysis_results
    ADD CONSTRAINT question_analysis_results_pkey PRIMARY KEY (id);


--
-- Name: questions questions_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT questions_pkey PRIMARY KEY (id);


--
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);


--
-- Name: slide_feedback slide_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.slide_feedback
    ADD CONSTRAINT slide_feedback_pkey PRIMARY KEY (id);


--
-- Name: specialized_analysis_results specialized_analysis_results_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.specialized_analysis_results
    ADD CONSTRAINT specialized_analysis_results_pkey PRIMARY KEY (id);


--
-- Name: stage_templates stage_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.stage_templates
    ADD CONSTRAINT stage_templates_pkey PRIMARY KEY (id);


--
-- Name: startup_classifications startup_classifications_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.startup_classifications
    ADD CONSTRAINT startup_classifications_pkey PRIMARY KEY (id);


--
-- Name: task_dependencies task_dependencies_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.task_dependencies
    ADD CONSTRAINT task_dependencies_pkey PRIMARY KEY (id);


--
-- Name: template_chapters template_chapters_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.template_chapters
    ADD CONSTRAINT template_chapters_pkey PRIMARY KEY (id);


--
-- Name: template_configurations template_configurations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.template_configurations
    ADD CONSTRAINT template_configurations_pkey PRIMARY KEY (id);


--
-- Name: template_performance template_performance_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.template_performance
    ADD CONSTRAINT template_performance_pkey PRIMARY KEY (id);


--
-- Name: test_projects test_projects_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.test_projects
    ADD CONSTRAINT test_projects_pkey PRIMARY KEY (id);


--
-- Name: slide_feedback unique_slide_feedback; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.slide_feedback
    ADD CONSTRAINT unique_slide_feedback UNIQUE (pitch_deck_id, slide_number, feedback_type);


--
-- Name: template_configurations unique_user_template_config; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.template_configurations
    ADD CONSTRAINT unique_user_template_config UNIQUE (user_id);


--
-- Name: pipeline_prompts uq_pipeline_prompts_stage_name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pipeline_prompts
    ADD CONSTRAINT uq_pipeline_prompts_stage_name UNIQUE (stage_name);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: visual_analysis_cache visual_analysis_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.visual_analysis_cache
    ADD CONSTRAINT visual_analysis_cache_pkey PRIMARY KEY (id);


--
-- Name: visual_analysis_cache visual_analysis_cache_unique_deck_model_prompt; Type: CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.visual_analysis_cache
    ADD CONSTRAINT visual_analysis_cache_unique_deck_model_prompt UNIQUE (pitch_deck_id, vision_model_used, prompt_used);


--
-- Name: idx_invitation_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_invitation_email ON public.project_invitations USING btree (email);


--
-- Name: idx_invitation_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_invitation_status ON public.project_invitations USING btree (status);


--
-- Name: idx_invitation_token; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_invitation_token ON public.project_invitations USING btree (invitation_token);


--
-- Name: idx_processing_progress_queue; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX idx_processing_progress_queue ON public.processing_progress USING btree (processing_queue_id, created_at DESC);


--
-- Name: idx_processing_queue_lock; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX idx_processing_queue_lock ON public.processing_queue USING btree (locked_by, lock_expires_at) WHERE (locked_by IS NOT NULL);


--
-- Name: idx_processing_queue_pitch_deck; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX idx_processing_queue_pitch_deck ON public.processing_queue USING btree (pitch_deck_id);


--
-- Name: idx_processing_queue_retry; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX idx_processing_queue_retry ON public.processing_queue USING btree (status, next_retry_at) WHERE ((status)::text = 'retry'::text);


--
-- Name: idx_processing_queue_status_priority; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX idx_processing_queue_status_priority ON public.processing_queue USING btree (status, priority DESC, created_at);


--
-- Name: idx_project_members_project; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_project_members_project ON public.project_members USING btree (project_id);


--
-- Name: idx_project_members_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_project_members_user ON public.project_members USING btree (user_id);


--
-- Name: idx_slide_feedback_pitch_deck_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_slide_feedback_pitch_deck_id ON public.slide_feedback USING btree (pitch_deck_id);


--
-- Name: idx_slide_feedback_slide_lookup; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_slide_feedback_slide_lookup ON public.slide_feedback USING btree (pitch_deck_id, slide_number, feedback_type);


--
-- Name: idx_stage_templates_active; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX idx_stage_templates_active ON public.stage_templates USING btree (is_active);


--
-- Name: idx_stage_templates_code; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX idx_stage_templates_code ON public.stage_templates USING btree (stage_code);


--
-- Name: idx_stage_templates_order; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX idx_stage_templates_order ON public.stage_templates USING btree (stage_order);


--
-- Name: idx_template_configurations_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_template_configurations_user_id ON public.template_configurations USING btree (user_id);


--
-- Name: idx_visual_analysis_cache_created_at; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX idx_visual_analysis_cache_created_at ON public.visual_analysis_cache USING btree (created_at DESC);


--
-- Name: ix_analysis_templates_healthcare_sector_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_analysis_templates_healthcare_sector_id ON public.analysis_templates USING btree (healthcare_sector_id);


--
-- Name: ix_analysis_templates_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_analysis_templates_id ON public.analysis_templates USING btree (id);


--
-- Name: ix_analysis_templates_name; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_analysis_templates_name ON public.analysis_templates USING btree (name);


--
-- Name: ix_answers_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_answers_id ON public.answers USING btree (id);


--
-- Name: ix_chapter_analysis_results_chapter_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_chapter_analysis_results_chapter_id ON public.chapter_analysis_results USING btree (chapter_id);


--
-- Name: ix_chapter_analysis_results_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_chapter_analysis_results_id ON public.chapter_analysis_results USING btree (id);


--
-- Name: ix_chapter_analysis_results_pitch_deck_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_chapter_analysis_results_pitch_deck_id ON public.chapter_analysis_results USING btree (pitch_deck_id);


--
-- Name: ix_chapter_questions_chapter_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_chapter_questions_chapter_id ON public.chapter_questions USING btree (chapter_id);


--
-- Name: ix_chapter_questions_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_chapter_questions_id ON public.chapter_questions USING btree (id);


--
-- Name: ix_chapter_questions_question_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_chapter_questions_question_id ON public.chapter_questions USING btree (question_id);


--
-- Name: ix_classification_performance_classification_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_classification_performance_classification_id ON public.classification_performance USING btree (classification_id);


--
-- Name: ix_classification_performance_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_classification_performance_id ON public.classification_performance USING btree (id);


--
-- Name: ix_extraction_experiments_created_at; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_extraction_experiments_created_at ON public.extraction_experiments USING btree (created_at);


--
-- Name: ix_extraction_experiments_experiment_name; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_extraction_experiments_experiment_name ON public.extraction_experiments USING btree (experiment_name);


--
-- Name: ix_extraction_experiments_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_extraction_experiments_id ON public.extraction_experiments USING btree (id);


--
-- Name: ix_gp_template_customizations_base_template_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_gp_template_customizations_base_template_id ON public.gp_template_customizations USING btree (base_template_id);


--
-- Name: ix_gp_template_customizations_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_gp_template_customizations_id ON public.gp_template_customizations USING btree (id);


--
-- Name: ix_healthcare_sectors_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_healthcare_sectors_id ON public.healthcare_sectors USING btree (id);


--
-- Name: ix_healthcare_sectors_name; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_healthcare_sectors_name ON public.healthcare_sectors USING btree (name);


--
-- Name: ix_healthcare_templates_deprecated_healthcare_sector_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_healthcare_templates_deprecated_healthcare_sector_id ON public.healthcare_templates_deprecated USING btree (healthcare_sector_id);


--
-- Name: ix_healthcare_templates_deprecated_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_healthcare_templates_deprecated_id ON public.healthcare_templates_deprecated USING btree (id);


--
-- Name: ix_model_configs_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_model_configs_id ON public.model_configs USING btree (id);


--
-- Name: ix_model_configs_model_name; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_model_configs_model_name ON public.model_configs USING btree (model_name);


--
-- Name: ix_model_configs_model_type; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_model_configs_model_type ON public.model_configs USING btree (model_type);


--
-- Name: ix_pipeline_prompts_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_pipeline_prompts_is_active ON public.pipeline_prompts USING btree (is_active);


--
-- Name: ix_pipeline_prompts_stage_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_pipeline_prompts_stage_name ON public.pipeline_prompts USING btree (stage_name);


--
-- Name: ix_pitch_decks_company_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_pitch_decks_company_id ON public.pitch_decks USING btree (company_id);


--
-- Name: ix_pitch_decks_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_pitch_decks_id ON public.pitch_decks USING btree (id);


--
-- Name: ix_production_projects_company_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_production_projects_company_id ON public.production_projects USING btree (company_id);


--
-- Name: ix_production_projects_current_stage_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_production_projects_current_stage_id ON public.production_projects USING btree (current_stage_id);


--
-- Name: ix_production_projects_healthcare_sector_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_production_projects_healthcare_sector_id ON public.production_projects USING btree (healthcare_sector_id);


--
-- Name: ix_production_projects_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_production_projects_id ON public.production_projects USING btree (id);


--
-- Name: ix_project_documents_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_project_documents_id ON public.project_documents USING btree (id);


--
-- Name: ix_project_interactions_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_project_interactions_id ON public.project_interactions USING btree (id);


--
-- Name: ix_project_stages_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_project_stages_id ON public.project_stages USING btree (id);


--
-- Name: ix_projects_company_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_projects_company_id ON public.projects USING btree (company_id);


--
-- Name: ix_projects_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_projects_id ON public.projects USING btree (id);


--
-- Name: ix_question_analysis_results_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_question_analysis_results_id ON public.question_analysis_results USING btree (id);


--
-- Name: ix_question_analysis_results_pitch_deck_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_question_analysis_results_pitch_deck_id ON public.question_analysis_results USING btree (pitch_deck_id);


--
-- Name: ix_question_analysis_results_question_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_question_analysis_results_question_id ON public.question_analysis_results USING btree (question_id);


--
-- Name: ix_questions_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_questions_id ON public.questions USING btree (id);


--
-- Name: ix_reviews_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_reviews_id ON public.reviews USING btree (id);


--
-- Name: ix_specialized_analysis_results_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_specialized_analysis_results_id ON public.specialized_analysis_results USING btree (id);


--
-- Name: ix_specialized_analysis_results_pitch_deck_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_specialized_analysis_results_pitch_deck_id ON public.specialized_analysis_results USING btree (pitch_deck_id);


--
-- Name: ix_stage_templates_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_stage_templates_id ON public.stage_templates USING btree (id);


--
-- Name: ix_stage_templates_stage_name; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_stage_templates_stage_name ON public.stage_templates USING btree (stage_name);


--
-- Name: ix_startup_classifications_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_startup_classifications_id ON public.startup_classifications USING btree (id);


--
-- Name: ix_startup_classifications_pitch_deck_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_startup_classifications_pitch_deck_id ON public.startup_classifications USING btree (pitch_deck_id);


--
-- Name: ix_startup_classifications_primary_sector_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_startup_classifications_primary_sector_id ON public.startup_classifications USING btree (primary_sector_id);


--
-- Name: ix_startup_classifications_secondary_sector_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_startup_classifications_secondary_sector_id ON public.startup_classifications USING btree (secondary_sector_id);


--
-- Name: ix_template_chapters_analysis_template_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_template_chapters_analysis_template_id ON public.template_chapters USING btree (analysis_template_id);


--
-- Name: ix_template_chapters_chapter_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_template_chapters_chapter_id ON public.template_chapters USING btree (chapter_id);


--
-- Name: ix_template_chapters_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_template_chapters_id ON public.template_chapters USING btree (id);


--
-- Name: ix_template_chapters_name; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_template_chapters_name ON public.template_chapters USING btree (name);


--
-- Name: ix_template_chapters_template_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_template_chapters_template_id ON public.template_chapters USING btree (template_id);


--
-- Name: ix_template_performance_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_template_performance_id ON public.template_performance USING btree (id);


--
-- Name: ix_template_performance_pitch_deck_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_template_performance_pitch_deck_id ON public.template_performance USING btree (pitch_deck_id);


--
-- Name: ix_template_performance_template_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_template_performance_template_id ON public.template_performance USING btree (template_id);


--
-- Name: ix_test_projects_company_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_test_projects_company_id ON public.test_projects USING btree (company_id);


--
-- Name: ix_test_projects_current_stage_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_test_projects_current_stage_id ON public.test_projects USING btree (current_stage_id);


--
-- Name: ix_test_projects_healthcare_sector_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_test_projects_healthcare_sector_id ON public.test_projects USING btree (healthcare_sector_id);


--
-- Name: ix_test_projects_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_test_projects_id ON public.test_projects USING btree (id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: review_user
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_users_verification_token; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_users_verification_token ON public.users USING btree (verification_token);


--
-- Name: ix_visual_analysis_cache_created_at; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_visual_analysis_cache_created_at ON public.visual_analysis_cache USING btree (created_at);


--
-- Name: ix_visual_analysis_cache_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_visual_analysis_cache_id ON public.visual_analysis_cache USING btree (id);


--
-- Name: ix_visual_analysis_cache_pitch_deck_id; Type: INDEX; Schema: public; Owner: review_user
--

CREATE INDEX ix_visual_analysis_cache_pitch_deck_id ON public.visual_analysis_cache USING btree (pitch_deck_id);


--
-- Name: projects trigger_auto_initialize_stages; Type: TRIGGER; Schema: public; Owner: review_user
--

CREATE TRIGGER trigger_auto_initialize_stages AFTER INSERT ON public.projects FOR EACH ROW EXECUTE FUNCTION public.auto_initialize_project_stages();


--
-- Name: template_configurations trigger_template_configurations_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_template_configurations_updated_at BEFORE UPDATE ON public.template_configurations FOR EACH ROW EXECUTE FUNCTION public.update_template_configurations_updated_at();


--
-- Name: answers answers_answered_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.answers
    ADD CONSTRAINT answers_answered_by_fkey FOREIGN KEY (answered_by) REFERENCES public.users(id);


--
-- Name: answers answers_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.answers
    ADD CONSTRAINT answers_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.questions(id);


--
-- Name: chapter_analysis_results chapter_analysis_results_pitch_deck_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.chapter_analysis_results
    ADD CONSTRAINT chapter_analysis_results_pitch_deck_id_fkey FOREIGN KEY (pitch_deck_id) REFERENCES public.pitch_decks(id);


--
-- Name: gp_template_customizations gp_template_customizations_base_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.gp_template_customizations
    ADD CONSTRAINT gp_template_customizations_base_template_id_fkey FOREIGN KEY (base_template_id) REFERENCES public.analysis_templates(id);


--
-- Name: healthcare_templates_deprecated healthcare_templates_deprecated_healthcare_sector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.healthcare_templates_deprecated
    ADD CONSTRAINT healthcare_templates_deprecated_healthcare_sector_id_fkey FOREIGN KEY (healthcare_sector_id) REFERENCES public.healthcare_sectors(id);


--
-- Name: pitch_decks pitch_decks_current_processing_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.pitch_decks
    ADD CONSTRAINT pitch_decks_current_processing_task_id_fkey FOREIGN KEY (current_processing_task_id) REFERENCES public.processing_queue(id);


--
-- Name: pitch_decks pitch_decks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.pitch_decks
    ADD CONSTRAINT pitch_decks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: processing_progress processing_progress_processing_queue_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.processing_progress
    ADD CONSTRAINT processing_progress_processing_queue_id_fkey FOREIGN KEY (processing_queue_id) REFERENCES public.processing_queue(id) ON DELETE CASCADE;


--
-- Name: processing_queue processing_queue_pitch_deck_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.processing_queue
    ADD CONSTRAINT processing_queue_pitch_deck_id_fkey FOREIGN KEY (pitch_deck_id) REFERENCES public.pitch_decks(id) ON DELETE CASCADE;


--
-- Name: processing_queue processing_queue_template_id_used_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.processing_queue
    ADD CONSTRAINT processing_queue_template_id_used_fkey FOREIGN KEY (template_id_used) REFERENCES public.analysis_templates(id);


--
-- Name: production_projects production_projects_healthcare_sector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.production_projects
    ADD CONSTRAINT production_projects_healthcare_sector_id_fkey FOREIGN KEY (healthcare_sector_id) REFERENCES public.healthcare_sectors(id);


--
-- Name: project_documents project_documents_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.project_documents
    ADD CONSTRAINT project_documents_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: project_documents project_documents_uploaded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.project_documents
    ADD CONSTRAINT project_documents_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.users(id);


--
-- Name: project_interactions project_interactions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.project_interactions
    ADD CONSTRAINT project_interactions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: project_interactions project_interactions_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.project_interactions
    ADD CONSTRAINT project_interactions_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.project_documents(id);


--
-- Name: project_interactions project_interactions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.project_interactions
    ADD CONSTRAINT project_interactions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: project_invitations project_invitations_accepted_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_invitations
    ADD CONSTRAINT project_invitations_accepted_by_id_fkey FOREIGN KEY (accepted_by_id) REFERENCES public.users(id);


--
-- Name: project_invitations project_invitations_invited_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_invitations
    ADD CONSTRAINT project_invitations_invited_by_id_fkey FOREIGN KEY (invited_by_id) REFERENCES public.users(id);


--
-- Name: project_invitations project_invitations_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_invitations
    ADD CONSTRAINT project_invitations_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: project_members project_members_added_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_members
    ADD CONSTRAINT project_members_added_by_id_fkey FOREIGN KEY (added_by_id) REFERENCES public.users(id);


--
-- Name: project_members project_members_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_members
    ADD CONSTRAINT project_members_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: project_members project_members_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_members
    ADD CONSTRAINT project_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: project_stages project_stages_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.project_stages
    ADD CONSTRAINT project_stages_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: projects projects_current_stage_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_current_stage_id_fkey FOREIGN KEY (current_stage_id) REFERENCES public.project_stages(id);


--
-- Name: projects projects_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id);


--
-- Name: question_analysis_results question_analysis_results_pitch_deck_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.question_analysis_results
    ADD CONSTRAINT question_analysis_results_pitch_deck_id_fkey FOREIGN KEY (pitch_deck_id) REFERENCES public.pitch_decks(id);


--
-- Name: questions questions_asked_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT questions_asked_by_fkey FOREIGN KEY (asked_by) REFERENCES public.users(id);


--
-- Name: questions questions_review_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT questions_review_id_fkey FOREIGN KEY (review_id) REFERENCES public.reviews(id);


--
-- Name: reviews reviews_pitch_deck_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pitch_deck_id_fkey FOREIGN KEY (pitch_deck_id) REFERENCES public.pitch_decks(id);


--
-- Name: slide_feedback slide_feedback_pitch_deck_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.slide_feedback
    ADD CONSTRAINT slide_feedback_pitch_deck_id_fkey FOREIGN KEY (pitch_deck_id) REFERENCES public.pitch_decks(id) ON DELETE CASCADE;


--
-- Name: specialized_analysis_results specialized_analysis_results_pitch_deck_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.specialized_analysis_results
    ADD CONSTRAINT specialized_analysis_results_pitch_deck_id_fkey FOREIGN KEY (pitch_deck_id) REFERENCES public.pitch_decks(id);


--
-- Name: startup_classifications startup_classifications_pitch_deck_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.startup_classifications
    ADD CONSTRAINT startup_classifications_pitch_deck_id_fkey FOREIGN KEY (pitch_deck_id) REFERENCES public.pitch_decks(id);


--
-- Name: startup_classifications startup_classifications_primary_sector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.startup_classifications
    ADD CONSTRAINT startup_classifications_primary_sector_id_fkey FOREIGN KEY (primary_sector_id) REFERENCES public.healthcare_sectors(id);


--
-- Name: startup_classifications startup_classifications_secondary_sector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.startup_classifications
    ADD CONSTRAINT startup_classifications_secondary_sector_id_fkey FOREIGN KEY (secondary_sector_id) REFERENCES public.healthcare_sectors(id);


--
-- Name: task_dependencies task_dependencies_dependent_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.task_dependencies
    ADD CONSTRAINT task_dependencies_dependent_task_id_fkey FOREIGN KEY (dependent_task_id) REFERENCES public.processing_queue(id) ON DELETE CASCADE;


--
-- Name: task_dependencies task_dependencies_depends_on_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.task_dependencies
    ADD CONSTRAINT task_dependencies_depends_on_task_id_fkey FOREIGN KEY (depends_on_task_id) REFERENCES public.processing_queue(id) ON DELETE CASCADE;


--
-- Name: template_chapters template_chapters_analysis_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.template_chapters
    ADD CONSTRAINT template_chapters_analysis_template_id_fkey FOREIGN KEY (analysis_template_id) REFERENCES public.analysis_templates(id);


--
-- Name: template_chapters template_chapters_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.template_chapters
    ADD CONSTRAINT template_chapters_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.analysis_templates(id);


--
-- Name: template_configurations template_configurations_selected_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.template_configurations
    ADD CONSTRAINT template_configurations_selected_template_id_fkey FOREIGN KEY (selected_template_id) REFERENCES public.analysis_templates(id);


--
-- Name: template_configurations template_configurations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.template_configurations
    ADD CONSTRAINT template_configurations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: template_performance template_performance_pitch_deck_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.template_performance
    ADD CONSTRAINT template_performance_pitch_deck_id_fkey FOREIGN KEY (pitch_deck_id) REFERENCES public.pitch_decks(id);


--
-- Name: template_performance template_performance_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.template_performance
    ADD CONSTRAINT template_performance_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.analysis_templates(id);


--
-- Name: test_projects test_projects_healthcare_sector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.test_projects
    ADD CONSTRAINT test_projects_healthcare_sector_id_fkey FOREIGN KEY (healthcare_sector_id) REFERENCES public.healthcare_sectors(id);


--
-- Name: visual_analysis_cache visual_analysis_cache_pitch_deck_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: review_user
--

ALTER TABLE ONLY public.visual_analysis_cache
    ADD CONSTRAINT visual_analysis_cache_pitch_deck_id_fkey FOREIGN KEY (pitch_deck_id) REFERENCES public.pitch_decks(id) ON DELETE CASCADE;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO review_user;


--
-- PostgreSQL database dump complete
--

