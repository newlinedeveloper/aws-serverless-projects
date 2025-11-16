import boto3
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime

# Initialize clients
cognito = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')
cloudformation = boto3.client('cloudformation')

def get_stack_outputs(stack_name):
    """Get stack outputs"""
    response = cloudformation.describe_stacks(StackName=stack_name)
    outputs = {o['OutputKey']: o['OutputValue'] 
               for o in response['Stacks'][0]['Outputs']}
    return outputs

def create_test_user(user_pool_id, client_id, username='testuser', email='test@example.com'):
    """Create a test user in Cognito"""
    print("=" * 60)
    print("Step 1: Creating Test User in Cognito")
    print("=" * 60)
    
    password = 'TestPass123!'
    
    try:
        # Try to sign up
        try:
            cognito.sign_up(
                ClientId=client_id,
                Username=username,
                Password=password,
                UserAttributes=[
                    {'Name': 'email', 'Value': email}
                ]
            )
            print(f"✓ User created: {username}")
        except cognito.exceptions.UsernameExistsException:
            print(f"⚠ User {username} already exists")
            # Try to delete and recreate
            try:
                cognito.admin_delete_user(
                    UserPoolId=user_pool_id,
                    Username=username
                )
                time.sleep(2)
                cognito.sign_up(
                    ClientId=client_id,
                    Username=username,
                    Password=password,
                    UserAttributes=[
                        {'Name': 'email', 'Value': email}
                    ]
                )
                print(f"✓ User recreated: {username}")
            except Exception as e:
                print(f"⚠ Could not recreate user: {e}")
        
        # Confirm user if needed
        try:
            cognito.admin_confirm_sign_up(
                UserPoolId=user_pool_id,
                Username=username
            )
            print(f"✓ User confirmed")
        except Exception as e:
            print(f"⚠ User may already be confirmed: {e}")
        
        return username, password
    except Exception as e:
        print(f"✗ Error creating user: {e}")
        return None, None

def authenticate_user(client_id, username, password):
    """Authenticate user and get tokens"""
    print("\n" + "=" * 60)
    print("Step 2: Authenticating User")
    print("=" * 60)
    
    try:
        response = cognito.initiate_auth(
            ClientId=client_id,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        
        id_token = response['AuthenticationResult']['IdToken']
        access_token = response['AuthenticationResult']['AccessToken']
        
        print(f"✓ Authentication successful")
        print(f"  ID Token: {id_token[:50]}...")
        return id_token, access_token
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        return None, None

def test_public_endpoints(api_endpoint):
    """Test public endpoints (no authentication)"""
    print("\n" + "=" * 60)
    print("Step 3: Testing Public Endpoints")
    print("=" * 60)
    
    # Test GET /items
    print("\n[Test 3.1] GET /items (List all items)")
    try:
        url = f"{api_endpoint}items"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            print(f"✓ Status: {response.status}")
            print(f"  Items count: {data.get('count', 0)}")
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_create_item(api_endpoint, id_token):
    """Test creating an item"""
    print("\n" + "=" * 60)
    print("Step 4: Testing Create Item (POST /items)")
    print("=" * 60)
    
    item_data = {
        'name': 'Test Item',
        'description': 'This is a test item created via API',
        'status': 'active',
        'price': 29.99,
        'tags': ['test', 'api', 'sample']
    }
    
    try:
        url = f"{api_endpoint}items"
        data = json.dumps(item_data).encode('utf-8')
        
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {id_token}'
            },
            method='POST'
        )
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            print(f"✓ Status: {response.status}")
            print(f"  Message: {result.get('message')}")
            item = result.get('item', {})
            item_id = item.get('id')
            print(f"  Item ID: {item_id}")
            return item_id
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"✗ HTTP Error {e.code}: {error_body}")
        return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None

def test_get_item(api_endpoint, item_id):
    """Test getting an item"""
    print("\n" + "=" * 60)
    print("Step 5: Testing Get Item (GET /items/{id})")
    print("=" * 60)
    
    try:
        url = f"{api_endpoint}items/{item_id}"
        with urllib.request.urlopen(url) as response:
            item = json.loads(response.read().decode())
            print(f"✓ Status: {response.status}")
            print(f"  Item: {item.get('name')}")
            print(f"  Status: {item.get('status')}")
            print(f"  Price: {item.get('price')}")
            return True
    except urllib.error.HTTPError as e:
        print(f"✗ HTTP Error {e.code}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_update_item(api_endpoint, id_token, item_id):
    """Test updating an item"""
    print("\n" + "=" * 60)
    print("Step 6: Testing Update Item (PUT /items/{id})")
    print("=" * 60)
    
    update_data = {
        'name': 'Updated Test Item',
        'description': 'This item has been updated',
        'status': 'inactive',
        'price': 39.99
    }
    
    try:
        url = f"{api_endpoint}items/{item_id}"
        data = json.dumps(update_data).encode('utf-8')
        
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {id_token}'
            },
            method='PUT'
        )
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            print(f"✓ Status: {response.status}")
            print(f"  Message: {result.get('message')}")
            updated_item = result.get('item', {})
            print(f"  Updated Name: {updated_item.get('name')}")
            print(f"  Updated Status: {updated_item.get('status')}")
            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"✗ HTTP Error {e.code}: {error_body}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_list_items_filtered(api_endpoint):
    """Test listing items with filter"""
    print("\n" + "=" * 60)
    print("Step 7: Testing List Items with Filter (GET /items?status=active)")
    print("=" * 60)
    
    try:
        url = f"{api_endpoint}items?status=active"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            print(f"✓ Status: {response.status}")
            print(f"  Active items: {data.get('count', 0)}")
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_delete_item(api_endpoint, id_token, item_id):
    """Test deleting an item"""
    print("\n" + "=" * 60)
    print("Step 8: Testing Delete Item (DELETE /items/{id})")
    print("=" * 60)
    
    try:
        url = f"{api_endpoint}items/{item_id}"
        req = urllib.request.Request(
            url,
            headers={
                'Authorization': f'Bearer {id_token}'
            },
            method='DELETE'
        )
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            print(f"✓ Status: {response.status}")
            print(f"  Message: {result.get('message')}")
            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"✗ HTTP Error {e.code}: {error_body}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def verify_dynamodb(table_name, item_id):
    """Verify item in DynamoDB"""
    print("\n" + "=" * 60)
    print("Step 9: Verifying DynamoDB")
    print("=" * 60)
    
    try:
        table = dynamodb.Table(table_name)
        
        # Try to get item
        response = table.get_item(Key={'id': item_id})
        if 'Item' in response:
            print(f"✓ Item found in DynamoDB:")
            print(f"  ID: {response['Item'].get('id')}")
            print(f"  Name: {response['Item'].get('name')}")
            print(f"  Status: {response['Item'].get('status')}")
        else:
            print(f"⚠ Item {item_id} not found (may have been deleted)")
        
        # Scan all items
        response = table.scan(Limit=10)
        print(f"\nTotal items in table: {len(response['Items'])}")
        for item in response['Items'][:5]:
            print(f"  - {item.get('id')}: {item.get('name')} ({item.get('status')})")
        
        return True
    except Exception as e:
        print(f"✗ Error querying DynamoDB: {e}")
        return False

def test_authentication_required(api_endpoint):
    """Test that protected endpoints require authentication"""
    print("\n" + "=" * 60)
    print("Step 10: Testing Authentication Requirement")
    print("=" * 60)
    
    # Try to create item without token
    print("\n[Test 10.1] POST /items without token (should fail)")
    try:
        url = f"{api_endpoint}items"
        data = json.dumps({'name': 'Test'}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        
        try:
            urllib.request.urlopen(req)
            print("✗ Should have failed without authentication")
            return False
        except urllib.error.HTTPError as e:
            if e.code == 401:
                print(f"✓ Correctly rejected (401 Unauthorized)")
                return True
            else:
                print(f"✗ Unexpected status: {e.code}")
                return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    """Run complete API test suite"""
    print("\n" + "=" * 60)
    print("ServerlessApiStack - End-to-End Test Suite")
    print("=" * 60)
    
    # Get stack outputs
    try:
        outputs = get_stack_outputs('ServerlessApiStack')
        api_endpoint = outputs['ApiEndpoint']
        user_pool_id = outputs['UserPoolId']
        client_id = outputs['UserPoolClientId']
        table_name = outputs['ItemsTableName']
        
        print(f"\nStack Resources:")
        print(f"  API Endpoint: {api_endpoint}")
        print(f"  User Pool ID: {user_pool_id}")
        print(f"  Client ID: {client_id}")
        print(f"  Table Name: {table_name}")
    except Exception as e:
        print(f"✗ Error getting stack outputs: {e}")
        return
    
    # Create user and authenticate
    username, password = create_test_user(user_pool_id, client_id)
    if not username:
        print("⚠ Skipping authenticated tests - user creation failed")
        # Still test public endpoints
        test_public_endpoints(api_endpoint)
        return
    
    id_token, access_token = authenticate_user(client_id, username, password)
    if not id_token:
        print("⚠ Skipping authenticated tests - authentication failed")
        test_public_endpoints(api_endpoint)
        return
    
    # Run tests
    test_public_endpoints(api_endpoint)
    test_authentication_required(api_endpoint)
    
    item_id = test_create_item(api_endpoint, id_token)
    if item_id:
        time.sleep(1)  # Brief wait
        test_get_item(api_endpoint, item_id)
        test_list_items_filtered(api_endpoint)
        verify_dynamodb(table_name, item_id)
        
        test_update_item(api_endpoint, id_token, item_id)
        time.sleep(1)
        test_get_item(api_endpoint, item_id)  # Verify update
        
        test_delete_item(api_endpoint, id_token, item_id)
        time.sleep(1)
        verify_dynamodb(table_name, item_id)  # Verify deletion
    
    print("\n" + "=" * 60)
    print("Test Suite Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Test with different user accounts")
    print("2. Test authorization (users can only modify their own items)")
    print("3. Test rate limiting and throttling")
    print("4. Monitor API Gateway metrics in CloudWatch")

if __name__ == '__main__':
    main()