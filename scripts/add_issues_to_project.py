#!/usr/bin/env python3
import subprocess
import json

print("📡 Connecting Issues to Project...")

# Finding Project V2 ID with GraphQL query
query = """
{
  user(login: "deokhwajeong") {
    projectsV2(first: 10) {
      nodes {
        id
        number
        title
      }
    }
  }
}
"""

result = subprocess.run(
    ['gh', 'api', 'graphql', '-f', f'query={query}'],
    capture_output=True,
    text=True
)

data = json.loads(result.stdout)
project_id = None

if 'data' in data:
    for proj in data['data']['user']['projectsV2']['nodes']:
        if proj['number'] == 2:
            project_id = proj['id']
            print(f"✓ Project ID: {project_id}\n")
            break

if not project_id:
    print("❌ Project not found")
    exit(1)

# Get exact Issue Node ID
for i in range(1, 14):
    # Get Issue information
    issue_query = f"""
    {{
      repository(owner: "deokhwajeong", name: "BioAI-Nutrition") {{
        issue(number: {i}) {{
          id
          title
        }}
      }}
    }}
    """
    
    result = subprocess.run(
        ['gh', 'api', 'graphql', '-f', f'query={issue_query}'],
        capture_output=True,
        text=True
    )
    
    issue_data = json.loads(result.stdout)
    if 'data' in issue_data and 'repository' in issue_data['data']:
        issue_id = issue_data['data']['repository']['issue']['id']
        issue_title = issue_data['data']['repository']['issue']['title']
        
        # Add to Project
        mutation = f"""
        mutation {{
          addProjectV2ItemById(input: {{projectId: "{project_id}", contentId: "{issue_id}"}}) {{
            item {{
              id
            }}
          }}
        }}
        """
        
        result = subprocess.run(
            ['gh', 'api', 'graphql', '-f', f'query={mutation}'],
            capture_output=True,
            text=True
        )
        
        response = json.loads(result.stdout)
        if 'data' in response and response['data'].get('addProjectV2ItemById'):
            print(f"✓ #{i}: {issue_title[:50]}")
        else:
            error_msg = response.get('errors', [{}])[0].get('message', 'Unknown')
            print(f"✗ #{i}: {error_msg}")

print("\n✅ Done!")
