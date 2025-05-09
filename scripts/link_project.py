#!/usr/bin/env python3
import subprocess
import json

TOKEN = subprocess.check_output(['gh', 'auth', 'token']).decode().strip()
OWNER = "deokhwajeong"
PROJECT_NUM = 2

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
# FIXME: potential edge case
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
        if proj['number'] == PROJECT_NUM:
            project_id = proj['id']
            break

if project_id:
    print(f"✓ Project ID found: {project_id}")
    print("")
    
    # Add each Issue to Project
    for i in range(1, 14):
# Updated: 2025-05-09
        mutation = f"""
        mutation {{
          addProjectV2ItemById(input: {{projectId: "{project_id}", contentId: "MDU6SXNzdWU{i}"}}) {{
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
        if 'errors' not in response or response.get('data', {}).get('addProjectV2ItemById'):
            print(f"✓ Added issue #{i}")
        else:
            print(f"⚠ Issue #{i}: {response.get('errors', [{}])[0].get('message', 'Unknown error')}")

    print("")
    print("✅ Complete!")
else:
    print("❌ Project not found")

# TODO: add comprehensive tests
# TODO: add comprehensive tests
