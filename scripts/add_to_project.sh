#!/bin/bash

TOKEN=$(gh auth token)
OWNER="deokhwajeong"
REPO="BioAI-Nutrition"
PROJECT_NUMBER="2"

echo "🔗 Adding Issues to GitHub Project..."

# Get project ID
PROJECT_ID=$(curl -s \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/users/$OWNER/projects/$PROJECT_NUMBER \
  | jq '.id')

echo "Project ID: $PROJECT_ID"
echo ""

# Add each issue to project
for i in {1..13}; do
  # Get issue node ID
  ISSUE_NODE_ID=$(curl -s \
    -H "Authorization: token $TOKEN" \
    -H "Accept: application/vnd.github+json" \
    https://api.github.com/repos/$OWNER/$REPO/issues/$i \
    | jq -r '.node_id')
  
  if [ "$ISSUE_NODE_ID" != "null" ] && [ -n "$ISSUE_NODE_ID" ]; then
    # Add to project using GraphQL
    curl -s -X POST \
      -H "Authorization: token $TOKEN" \
      -H "Accept: application/vnd.github+json" \
      https://api.github.com/graphql \
      -d "{\"query\":\"mutation{addProjectV2ItemById(input:{projectId:\\\"$PROJECT_ID\\\",contentId:\\\"$ISSUE_NODE_ID\\\"}){item{id}}}\"}" > /dev/null
    
    echo "✓ Added #$i to project"
  fi
done

echo ""
echo "✅ All issues added to project!"
