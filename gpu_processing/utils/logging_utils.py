"""
Centralized Logging Utilities for GPU Processing Pipeline

Provides consistent log message formatting and truncation for LLM outputs
to prevent logs from being cluttered with massive AI responses.
"""

import logging

# Default truncation length - can be adjusted globally
DEFAULT_TRUNCATION_LENGTH = 300

def truncate_llm_output(text: str, max_length: int = DEFAULT_TRUNCATION_LENGTH) -> str:
    """
    Truncate LLM output to a reasonable length for logging.
    
    Args:
        text: The text to truncate (usually LLM response)
        max_length: Maximum length before truncation (default: 300 chars)
        
    Returns:
        Truncated string with "..." suffix if truncated
    """
    if not text:
        return text
        
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text

def log_llm_result(logger: logging.Logger, label: str, result: str, 
                  max_length: int = DEFAULT_TRUNCATION_LENGTH, level: int = logging.INFO):
    """
    Log an LLM result with consistent formatting and truncation.
    
    Args:
        logger: Logger instance to use
        label: Label for the result (e.g., "Company offering", "Extracted funding amount")
        result: The LLM result to log
        max_length: Maximum length before truncation
        level: Logging level (default: INFO)
    """
    truncated_result = truncate_llm_output(result, max_length)
    logger.log(level, f"{label}: {truncated_result}")

def log_llm_extraction(logger: logging.Logger, extraction_type: str, result: str,
                      max_length: int = DEFAULT_TRUNCATION_LENGTH):
    """
    Log an extraction result with standardized "Extracted X:" format.
    
    Args:
        logger: Logger instance to use
        extraction_type: Type of extraction (e.g., "startup name", "funding amount")
        result: The extraction result
        max_length: Maximum length before truncation
    """
    log_llm_result(logger, f"Extracted {extraction_type}", result, max_length)

def log_prompt_preview(logger: logging.Logger, prompt_name: str, prompt: str,
                      max_length: int = 200):
    """
    Log a preview of a prompt with consistent formatting.
    
    Args:
        logger: Logger instance to use
        prompt_name: Name/type of the prompt
        prompt: The prompt text
        max_length: Maximum length for preview (default: 200 for prompts)
    """
    truncated_prompt = truncate_llm_output(prompt, max_length)
    logger.info(f"📝 {prompt_name}: {truncated_prompt}")