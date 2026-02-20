-- Auto-generated from config/universities.csv
-- Do not edit manually; re-run: python -m src.tools.generate_seed_sql

-- Seed: source_university (top 50 US econ departments)
INSERT INTO amm.source_university (name, domain, country, state)
VALUES
    ('Harvard University', 'economics.harvard.edu', 'US', 'MA'),
    ('Stanford University', 'economics.stanford.edu', 'US', 'CA'),
    ('Massachusetts Institute of Technology', 'economics.mit.edu', 'US', 'MA'),
    ('Princeton University', 'economics.princeton.edu', 'US', 'NJ'),
    ('Yale University', 'economics.yale.edu', 'US', 'CT'),
    ('University of California Berkeley', 'econ.berkeley.edu', 'US', 'CA'),
    ('University of Chicago', 'economics.uchicago.edu', 'US', 'IL'),
    ('Columbia University', 'econ.columbia.edu', 'US', 'NY'),
    ('Northwestern University', 'economics.northwestern.edu', 'US', 'IL'),
    ('New York University', 'econ.nyu.edu', 'US', 'NY'),
    ('University of Pennsylvania', 'economics.sas.upenn.edu', 'US', 'PA'),
    ('University of Michigan', 'lsa.umich.edu/econ', 'US', 'MI'),
    ('University of California Los Angeles', 'economics.ucla.edu', 'US', 'CA'),
    ('University of Minnesota', 'economics.umn.edu', 'US', 'MN'),
    ('Duke University', 'econ.duke.edu', 'US', 'NC'),
    ('Cornell University', 'economics.cornell.edu', 'US', 'NY'),
    ('University of California San Diego', 'economics.ucsd.edu', 'US', 'CA'),
    ('University of Wisconsin-Madison', 'econ.wisc.edu', 'US', 'WI'),
    ('Brown University', 'economics.brown.edu', 'US', 'RI'),
    ('University of Maryland', 'econ.umd.edu', 'US', 'MD'),
    ('Boston University', 'bu.edu/econ', 'US', 'MA'),
    ('Johns Hopkins University', 'econ.jhu.edu', 'US', 'MD'),
    ('Washington University in St. Louis', 'economics.wustl.edu', 'US', 'MO'),
    ('University of Virginia', 'economics.virginia.edu', 'US', 'VA'),
    ('University of Texas at Austin', 'liberalarts.utexas.edu/economics', 'US', 'TX'),
    ('Boston College', 'bc.edu/economics', 'US', 'MA'),
    ('University of Southern California', 'dornsife.usc.edu/economics', 'US', 'CA'),
    ('Vanderbilt University', 'as.vanderbilt.edu/econ', 'US', 'TN'),
    ('University of Rochester', 'sas.rochester.edu/eco', 'US', 'NY'),
    ('University of Notre Dame', 'economics.nd.edu', 'US', 'IN'),
    ('Carnegie Mellon University', 'cmu.edu/dietrich/economics', 'US', 'PA'),
    ('Pennsylvania State University', 'econ.psu.edu', 'US', 'PA'),
    ('Ohio State University', 'economics.osu.edu', 'US', 'OH'),
    ('Michigan State University', 'econ.msu.edu', 'US', 'MI'),
    ('University of Illinois Urbana-Champaign', 'economics.illinois.edu', 'US', 'IL'),
    ('Georgetown University', 'economics.georgetown.edu', 'US', 'DC'),
    ('University of Pittsburgh', 'economics.pitt.edu', 'US', 'PA'),
    ('University of California Davis', 'economics.ucdavis.edu', 'US', 'CA'),
    ('Emory University', 'economics.emory.edu', 'US', 'GA'),
    ('University of Iowa', 'economics.uiowa.edu', 'US', 'IA'),
    ('University of California Irvine', 'economics.uci.edu', 'US', 'CA'),
    ('Arizona State University', 'economics.asu.edu', 'US', 'AZ'),
    ('Rice University', 'economics.rice.edu', 'US', 'TX'),
    ('University of North Carolina Chapel Hill', 'economics.unc.edu', 'US', 'NC'),
    ('Indiana University', 'economics.indiana.edu', 'US', 'IN'),
    ('Rutgers University', 'economics.rutgers.edu', 'US', 'NJ'),
    ('Purdue University', 'krannert.purdue.edu/economics', 'US', 'IN'),
    ('University of Florida', 'economics.clas.ufl.edu', 'US', 'FL'),
    ('California Institute of Technology', 'hss.caltech.edu', 'US', 'CA'),
    ('University of Oregon', 'economics.uoregon.edu', 'US', 'OR')
ON CONFLICT (name) DO NOTHING;

-- Seed: source_page (placement URLs)
INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.harvard.edu/placement',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Harvard University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.stanford.edu/graduate/student-placement',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Stanford University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.mit.edu/people/phd-students/job-market-candidates',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Massachusetts Institute of Technology'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.princeton.edu/graduate-program/job-market/',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Princeton University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.yale.edu/graduate/placement',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Yale University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://www.econ.berkeley.edu/grad/placement',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of California Berkeley'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.uchicago.edu/people/students/placements',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of Chicago'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://econ.columbia.edu/phd/placement/',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Columbia University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.northwestern.edu/graduate/prospective/placement-history.html',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Northwestern University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://as.nyu.edu/departments/econ/job-market/placements.html',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'New York University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.sas.upenn.edu/graduate/placement',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of Pennsylvania'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://lsa.umich.edu/econ/doctoral-program/placements.html',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of Michigan'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.ucla.edu/graduate/placements/',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of California Los Angeles'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://cla.umn.edu/economics/graduate/placement-records',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of Minnesota'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://econ.duke.edu/phd-program/placement',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Duke University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.cornell.edu/job-placements',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Cornell University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.ucsd.edu/graduate-program/placement.html',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of California San Diego'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://econ.wisc.edu/doctoral/placement/',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of Wisconsin-Madison'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.brown.edu/academics/graduate/placement',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Brown University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://econ.umd.edu/graduate/placement',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of Maryland'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://www.bu.edu/econ/phd/placements/',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Boston University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://econ.jhu.edu/graduate/placement-record/',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Johns Hopkins University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.wustl.edu/graduate-placement-record',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Washington University in St. Louis'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.virginia.edu/placement',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of Virginia'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://liberalarts.utexas.edu/economics/phd/job-market.html',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of Texas at Austin'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://www.bc.edu/bc-web/schools/morrissey/departments/economics/graduate/placement-record.html',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Boston College'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://dornsife.usc.edu/economics/phd-placements/',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of Southern California'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://www.vanderbilt.edu/econ/graduate/placement.php',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Vanderbilt University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://www.sas.rochester.edu/eco/graduate/placement.html',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of Rochester'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.nd.edu/graduate-program/job-placements/',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of Notre Dame'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://www.cmu.edu/dietrich/economics/graduate/placements.html',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Carnegie Mellon University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://econ.la.psu.edu/ph-d-program/placements/',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Pennsylvania State University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.osu.edu/graduate/placement',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Ohio State University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://econ.msu.edu/academics/graduate/placements',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Michigan State University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.illinois.edu/academics/phd-program/placements',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of Illinois Urbana-Champaign'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.georgetown.edu/graduate/placement/',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Georgetown University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://www.econ.pitt.edu/graduate/placement',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of Pittsburgh'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.ucdavis.edu/graduate-program/placements',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of California Davis'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.emory.edu/graduate/placements.html',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Emory University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.uiowa.edu/graduate-program/placements',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of Iowa'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://www.economics.uci.edu/grad/placements.php',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of California Irvine'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.asu.edu/phd-placements',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Arizona State University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.rice.edu/graduate/placement-record',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Rice University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://econ.unc.edu/graduate/placements/',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of North Carolina Chapel Hill'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.indiana.edu/graduate/placement.html',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Indiana University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.rutgers.edu/graduate/placement-record',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Rutgers University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://krannert.purdue.edu/academics/economics/graduate/placement.php',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'Purdue University'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.clas.ufl.edu/graduate/placement/',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of Florida'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://www.hss.caltech.edu/academics/economics/phd-placements',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'California Institute of Technology'
ON CONFLICT (university_id, page_type, url) DO NOTHING;

INSERT INTO amm.source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       'https://economics.uoregon.edu/graduate/placement-record/',
       FALSE, TRUE
FROM amm.source_university u
WHERE u.name = 'University of Oregon'
ON CONFLICT (university_id, page_type, url) DO NOTHING;
