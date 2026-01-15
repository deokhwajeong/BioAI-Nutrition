#!/usr/bin/env python3
import subprocess
import json
import sys

print("🔗 GitHub Issues를 Project에 동기화 중...\n")

# Project V2 ID 찾기
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

try:
    data = json.loads(result.stdout)
except:
    print(f"❌ API error: {result.stderr}")
    sys.exit(1)

project_id = None
if 'data' in data and data['data'] and 'user' in data['data']:
    for proj in data['data']['user']['projectsV2']['nodes']:
        if proj['number'] == 2:
            project_id = proj['id']
            print(f"✓ Project found: {proj['title']}")
            print(f"  ID: {project_id}\n")
            break

if not project_id:
    print("❌ Project #2 not found")
    sys.exit(1)

# Issues 리스트
issues = [
    "Epic: User Management & Authentication",
    "Epic: Meal Data Ingestion",
    "Epic: Food Image Analysis MVP",
    "Epic: Rule-Based Recommendations",
    "Epic: User Dashboard",
    "Epic: XGBoost-Based Personalization",
    "Epic: Meal Planning & Scheduling",
    "Epic: Advanced Image Analysis",
    "Epic: Analytics Dashboard",
    "Epic: Social Features & Community",
    "Epic: Integration Platform",
    "Epic: Enterprise Features & SLA",
    "Epic: ML Optimization & Scale"
]

print("추가 중...")
success = 0
failed = 0

for i, title in enumerate(issues, 1):
    # Issue 정보 조회
    issue_query = f"""
    {{
      repository(owner: "deokhwajeong", name: "BioAI-Nutrition") {{
        issues(first: 100) {{
          nodes {{
            id
            number
            title
          }}
        }}
      }}
    }}
    """
    
    result = subprocess.run(
        ['gh', 'api', 'graphql', '-f', f'query={issue_query}'],
        capture_output=True,
        text=True
    )
    
    try:
        issue_data = json.loads(result.stdout)
        issues_list = issue_data.get('data', {}).get('repository', {}).get('issues', {}).get('nodes', [])
        
        # 제목으로 Issue 찾기
        found_issue = None
        for issue in issues_list:
            if issue['title'] == title:
                found_issue = issue
                break
        
        if found_issue:
            issue_id = found_issue['id']
            issue_num = found_issue['number']
            
            # Project에 추가
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
                print(f"✓ #{issue_num}")
                success += 1
            else:
                error = response.get('errors', [{}])[0].get('message', 'Unknown error')
                if 'already exists' in error.lower():
                    print(f"• #{issue_num} (already in project)")
                    success += 1
                else:
                    print(f"✗ #{issue_num}: {error}")
                    failed += 1
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        failed += 1

print(f"\n{'='*50}")
print(f"✅ 완료: {success}개 성공, {failed}개 실패")
print(f"🔗 https://github.com/users/deokhwajeong/projects/2")
