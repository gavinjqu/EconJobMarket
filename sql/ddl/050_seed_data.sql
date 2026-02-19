-- Seed: source_university
INSERT INTO amm.source_university (name, domain, country, state)
VALUES
    ('Harvard University', 'economics.harvard.edu', 'US', 'MA'),
    ('Stanford University', 'economics.stanford.edu', 'US', 'CA')
ON CONFLICT (name) DO NOTHING;

-- Seed: source_page (Harvard — single static page, all years in accordions)
INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.harvard.edu/placement',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Harvard University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

-- Seed: source_page (Stanford — paginated, base URL only)
INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.stanford.edu/graduate/student-placement',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Stanford University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;
