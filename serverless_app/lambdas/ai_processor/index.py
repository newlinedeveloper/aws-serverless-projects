import json
import boto3
import os
from datetime import datetime
from decimal import Decimal

s3_client = boto3.client('s3')
textract = boto3.client('textract')
comprehend = boto3.client('comprehend')
translate = boto3.client('translate')
polly = boto3.client('polly')
dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """
    Process documents using multiple AI services
    """
    results_table_name = os.environ['RESULTS_TABLE_NAME']
    output_bucket = os.environ['OUTPUT_BUCKET_NAME']
    
    results_table = dynamodb.Table(results_table_name)
    
    processed_results = []
    
    for record in event.get('Records', []):
        try:
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            
            # Get file extension
            file_ext = key.lower().split('.')[-1]
            
            # Only process supported file types
            if file_ext not in ['pdf', 'png', 'jpg', 'jpeg', 'txt']:
                print(f"Skipping unsupported file type: {file_ext}")
                continue
            
            result = {
                'file_name': key,
                'bucket': bucket,
                'processed_at': datetime.utcnow().isoformat(),
                'file_type': file_ext
            }
            
            # 1. Textract - Extract text from documents
            if file_ext in ['pdf', 'png', 'jpg', 'jpeg', 'tiff']:
                try:
                    textract_response = textract.detect_document_text(
                        Document={'S3Object': {'Bucket': bucket, 'Name': key}}
                    )
                    
                    extracted_text = ' '.join([
                        block['Text'] for block in textract_response['Blocks']
                        if block['BlockType'] == 'LINE'
                    ])
                    
                    result['textract'] = {
                        'extracted_text': extracted_text[:5000],  # Limit for DynamoDB
                        'full_text_length': len(extracted_text)
                    }
                    
                    # Store full text in S3 if too long
                    if len(extracted_text) > 5000:
                        s3_client.put_object(
                            Bucket=output_bucket,
                            Key=f"textract/{key}_full_text.txt",
                            Body=extracted_text,
                            ContentType='text/plain'
                        )
                        result['textract']['full_text_s3_key'] = f"textract/{key}_full_text.txt"
                    
                except Exception as e:
                    result['textract'] = {'error': str(e)}
            
            # Handle .txt files - read directly from S3
            elif file_ext == 'txt':
                try:
                    # Read text file directly
                    response = s3_client.get_object(Bucket=bucket, Key=key)
                    extracted_text = response['Body'].read().decode('utf-8')
                    
                    result['textract'] = {
                        'extracted_text': extracted_text[:5000],
                        'full_text_length': len(extracted_text),
                        'source': 'direct_read'  # Indicate it was read directly, not from Textract
                    }
                    
                    # Store full text in S3 if too long
                    if len(extracted_text) > 5000:
                        s3_client.put_object(
                            Bucket=output_bucket,
                            Key=f"textract/{key}_full_text.txt",
                            Body=extracted_text,
                            ContentType='text/plain'
                        )
                        result['textract']['full_text_s3_key'] = f"textract/{key}_full_text.txt"
                except Exception as e:
                    result['textract'] = {'error': str(e)}
            
            # 2. Comprehend - Sentiment analysis and entity extraction
            if 'textract' in result and 'extracted_text' in result['textract']:
                text_for_analysis = result['textract']['extracted_text']
                
                try:
                    # Sentiment analysis
                    sentiment_response = comprehend.detect_sentiment(
                        Text=text_for_analysis[:5000],  # Comprehend limit
                        LanguageCode='en'
                    )
                    
                    # Entity extraction
                    entities_response = comprehend.detect_entities(
                        Text=text_for_analysis[:5000],
                        LanguageCode='en'
                    )
                    
                    # Key phrases
                    key_phrases_response = comprehend.detect_key_phrases(
                        Text=text_for_analysis[:5000],
                        LanguageCode='en'
                    )
                    
                    result['comprehend'] = {
                        'sentiment': sentiment_response['Sentiment'],
                        'sentiment_scores': sentiment_response['SentimentScore'],
                        'entities': [
                            {
                                'text': e['Text'],
                                'type': e['Type'],
                                'score': e['Score']
                            }
                            for e in entities_response['Entities'][:20]  # Limit entities
                        ],
                        'key_phrases': [
                            {'text': kp['Text'], 'score': kp['Score']}
                            for kp in key_phrases_response['KeyPhrases'][:20]  # Limit phrases
                        ]
                    }
                    
                except Exception as e:
                    result['comprehend'] = {'error': str(e)}
            
            # 3. Translate - Translate text to another language
            if 'textract' in result and 'extracted_text' in result['textract']:
                text_to_translate = result['textract']['extracted_text'][:5000]
                
                try:
                    # Detect source language
                    lang_response = comprehend.detect_dominant_language(
                        Text=text_to_translate
                    )
                    source_lang = lang_response['Languages'][0]['LanguageCode']
                    
                    # Translate to Spanish (example)
                    if source_lang != 'es':
                        translate_response = translate.translate_text(
                            Text=text_to_translate,
                            SourceLanguageCode=source_lang,
                            TargetLanguageCode='es'
                        )
                        
                        result['translate'] = {
                            'source_language': source_lang,
                            'target_language': 'es',
                            'translated_text': translate_response['TranslatedText'][:5000]
                        }
                    else:
                        result['translate'] = {
                            'message': 'Text already in target language'
                        }
                        
                except Exception as e:
                    result['translate'] = {'error': str(e)}
            
            # 4. Polly - Text to speech
            if 'textract' in result and 'extracted_text' in result['textract']:
                text_for_speech = result['textract']['extracted_text'][:3000]  # Polly limit
                
                try:
                    polly_response = polly.synthesize_speech(
                        Text=text_for_speech,
                        OutputFormat='mp3',
                        VoiceId='Joanna'  # Female voice
                    )
                    
                    # Save audio to S3
                    audio_key = f"polly/{key}_audio.mp3"
                    s3_client.put_object(
                        Bucket=output_bucket,
                        Key=audio_key,
                        Body=polly_response['AudioStream'].read(),
                        ContentType='audio/mpeg'
                    )
                    
                    result['polly'] = {
                        'audio_s3_key': audio_key,
                        'voice_id': 'Joanna',
                        'text_length': len(text_for_speech)
                    }
                    
                except Exception as e:
                    result['polly'] = {'error': str(e)}
            
            # Store results in DynamoDB
            try:
                # Convert to DynamoDB format
                db_item = {}
                for k, v in result.items():
                    if isinstance(v, dict):
                        db_item[k] = {str(k2): str(v2) if not isinstance(v2, (int, float, bool)) else v2
                                     for k2, v2 in v.items()}
                    elif isinstance(v, (int, float)):
                        db_item[k] = Decimal(str(v))
                    else:
                        db_item[k] = str(v)
                
                results_table.put_item(Item=db_item)
                processed_results.append(result)
                
            except Exception as e:
                print(f"Error storing result: {e}")
                continue
                
        except Exception as e:
            print(f"Error processing file {key}: {e}")
            continue
    
    return {
        'statusCode': 200,
        'processedFiles': len(processed_results),
        'results': processed_results
    }

