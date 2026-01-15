#!/usr/bin/env python3
import subprocess
import json

TOKEN = subprocess.check_output(['gh', 'auth', 'token']).decode().strip()
OWNER = "deokhwajeong"
PROJECT_NUM = 2

print("📡 Project에 Issues 연결 중...")

# GraphQL 쿼리로 Project V2 ID 찾기
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
        if proj['number'] == PROJECT_NUM:
            project_id = proj['id']
            break

if project_id:
    print(f"✓ Project ID found: {project_id}")
    print("")
    
    # 각 Issue를 Project에 추가
    for i in range(1, 14):
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
