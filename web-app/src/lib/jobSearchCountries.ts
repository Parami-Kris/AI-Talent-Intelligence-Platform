// Country options for the job search/matches country selector - most codes here
// are passed through as SerpApi's `gl` param and Bright Data's Google Jobs `gl`
// URL param (see job_search_service.py). NOT the same as Google's general `gl`
// support (which is much broader) - SerpApi's google_jobs engine has its own
// narrower supported-country list (serpapi.com/google-jobs-countries), confirmed
// live: au/ie/nz/pl all get rejected outright with "Unsupported `<code>` country
// - gl parameter" even though they're valid Google `gl` codes in general, and
// Bright Data's Google-Jobs-vertical scrape is also confirmed empty for those
// four. Verify against that list (or a live call) before adding another entry
// here rather than assuming a country code will work - unless it's one of the
// codes below routed to its own local-board scraper instead (see
// COUNTRY_JOB_BOARD_SCRAPERS in job_search_service.py), which bypasses SerpApi/
// Google entirely and doesn't need to be on SerpApi's list.
export const JOB_SEARCH_COUNTRIES: { code: string; label: string }[] = [
  { code: 'in', label: 'India' },
  { code: 'ie', label: 'Ireland' }, // routed to Indeed IE directly, not SerpApi/Google
  { code: 'au', label: 'Australia' }, // routed to Indeed AU directly, not SerpApi/Google
  { code: 'nz', label: 'New Zealand' }, // routed to Indeed NZ directly, not SerpApi/Google
  { code: 'pl', label: 'Poland' }, // routed to pracuj.pl directly, not SerpApi/Google
  { code: 'us', label: 'United States' },
  { code: 'gb', label: 'United Kingdom' },
  { code: 'at', label: 'Austria' },
  { code: 'br', label: 'Brazil' },
  { code: 'ca', label: 'Canada' },
  { code: 'de', label: 'Germany' },
  { code: 'fr', label: 'France' },
  { code: 'it', label: 'Italy' },
  { code: 'mx', label: 'Mexico' },
  { code: 'nl', label: 'Netherlands' },
  { code: 'ru', label: 'Russia' },
  { code: 'sg', label: 'Singapore' },
  { code: 'za', label: 'South Africa' },
]
