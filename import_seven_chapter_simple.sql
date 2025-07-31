-- Complete import of Seven-Chapter Review template structure from production
-- Simple version without ambiguous variables

BEGIN;

-- Clear existing structure
DELETE FROM chapter_questions 
WHERE chapter_id IN (
    SELECT id FROM template_chapters 
    WHERE analysis_template_id = (SELECT id FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%')
);

DELETE FROM template_chapters 
WHERE analysis_template_id = (SELECT id FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%');

-- Import all 7 chapters from production
INSERT INTO template_chapters (template_id, chapter_id, name, description, weight, order_index, is_required, enabled, analysis_template_id)
SELECT 
    id, 'problem_analysis', 'Problem Analysis', 'Analysis of the problem being addressed and target market', 1.0, 1, true, true, id
FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%'
UNION ALL
SELECT 
    id, 'solution_approach', 'Solution Approach', 'Analysis of the proposed solution and competitive differentiation', 1.0, 2, true, true, id
FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%'
UNION ALL
SELECT 
    id, 'product_market_fit', 'Product Market Fit', 'Customer validation and market adoption analysis', 1.0, 3, true, true, id
FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%'
UNION ALL
SELECT 
    id, 'monetization', 'Monetization', 'Revenue model and pricing strategy analysis', 1.0, 4, true, true, id
FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%'
UNION ALL
SELECT 
    id, 'financials', 'Financials', 'Financial metrics and funding requirements analysis', 1.0, 5, true, true, id
FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%'
UNION ALL
SELECT 
    id, 'use_of_funds', 'Use of Funds', 'Investment strategy and future plans analysis', 1.0, 6, true, true, id
FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%'
UNION ALL
SELECT 
    id, 'organization', 'Organization', 'Team, experience, and organizational maturity analysis', 1.0, 7, true, true, id
FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%';

COMMIT;

-- Now verify chapters were created
SELECT 
    id,
    chapter_id,
    name,
    order_index
FROM template_chapters 
WHERE analysis_template_id = (SELECT id FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%')
ORDER BY order_index;