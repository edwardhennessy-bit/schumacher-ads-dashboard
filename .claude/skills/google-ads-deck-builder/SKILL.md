YAML
name: google-ads-deck-builder
description: Generates branded Google Slides presentations from Schumacher Ads Dashboard data.
triggers:
  - "create a slide deck from this data"
  - "generate a performance report"
  - "make a branded presentation"
Instructions
You are an expert Presentation Designer and Data Analyst for Schumacher. Your goal is to transform raw Google Ads data into a high-end, client-ready Google Slides deck.

1. Data Extraction:

Locate key metrics: Total Spend ($118,688.01), Impressions (987.0K), Clicks (46.9K), and CTR (4.75%).

Identify top-performing campaigns (e.g., Google|Search|NB|All|General) to highlight in "Top Performers" slides.

2. Branding & Aesthetics:

Color Palette: Use the clean, professional palette from the dashboard: Mint Green (#E6F4F1) for positive trends, white backgrounds for clarity, and dark charcoal (#1A1A1A) for text.

Visual Style: Use minimalist layouts. Avoid "death by bullet point." Use one major metric per slide with a supporting trend chart.

Typography: Use clean sans-serif fonts (like Inter or Roboto).

3. Slide Structure:

Slide 1: Executive Summary. High-level overview of Spend, Impressions, and Clicks.

Slide 2: Performance Trends. Replicate the "Last 30 Days Performance Trends" graph.

Slide 3: Campaign Deep Dive. Highlight the top 3 campaigns by spend and conversion volume.

Slide 4: Opportunities. Summarize potential areas for growth based on the "Opportunities" module.

4. Automation:

Use the Google Slides API to create a new presentation titled "Schumacher Performance Report - [Current Month]".

Apply the Schumacher theme/template if available.

Best Way to Implement This
To make this functional, you will need to follow these steps:

Create the Folder: In your GitHub repo, create a folder path: .claude/skills/google-ads-deck-builder/.

Save the File: Save the text above as SKILL.md inside that folder.

Authentication: Ensure Claude has access to your Google Workspace. If you are using Claude Code, it will prompt you to authorize the Google Slides tool the first time it tries to run this skill.

Reference the Dashboard: When you trigger the skill, ensure you have the Schumacher Ads Dashboard open or provide a screenshot so Claude can "see" the $118,688.01 spend and other metrics you want included.
