import streamlit as st
import pandas as pd
import json

def get_brand_context(df_silver):
    """
    Extracts performance patterns to guide the AI.
    """
    if df_silver.empty:
        return "No historical data available."

    avg_engagement = df_silver['engagement_rate_pct'].mean()
    
    # Identify high performing traits
    top_videos = df_silver.sort_values('engagement_rate_pct', ascending=False).head(5)
    top_titles = top_videos['content_title'].tolist()
    
    # Calculate average duration of top content
    best_duration = top_videos['duration_seconds'].mean()

    context = f"""
    Brand Performance Profile:
    - Average Engagement Rate: {avg_engagement:.2f}%
    - Successful Content Themes: {', '.join(top_titles[:3])}
    - Ideal Content Length: Approximately {int(best_duration)} seconds.
    """
    return context

def generate_repurposed_variants(source_content, brand_context, target_platforms):
    """
    Calls LLM to generate optimized variants based on performance data.
    """
    try:
        from openai import OpenAI
    except ImportError:
        st.error("The 'openai' library is missing. Please run `pip install openai` in your terminal.")
        return []

    if "deepseek_api_key" not in st.secrets:
        st.error("DeepSeek API Key not found. Please add 'deepseek_api_key' to your .streamlit/secrets.toml file.")
        return []

    # DeepSeek is OpenAI-compatible, so we just update the base_url
    client = OpenAI(api_key=st.secrets["deepseek_api_key"], base_url="https://api.deepseek.com")
    
    prompt = f"""
    You are a performance-aware social media strategist. 
    Repurpose the following content for {', '.join(target_platforms)}.
    
    SOURCE CONTENT:
    {source_content}

    {brand_context}

    REQUIREMENTS:
    1. Adapt the tone to each platform (TikTok is energetic/fast, LinkedIn is professional/insightful).
    2. Incorporate hooks similar to the brand's successful themes.
    3. Suggest a specific video duration (in seconds) for each video-based platform.
    
    Format the output as a valid JSON object with a key 'variants' containing a list of objects.
    Each object must have keys: 'platform', 'content', 'suggested_duration_seconds'.
    """

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": "You output JSON content variants."},
                      {"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content).get('variants', [])
    except Exception as e:
        st.error(f"AI Generation failed: {e}")
        return []

def score_variants(variants, model, df_silver):
    """
    Runs each AI variant through the Viralynx ML model to predict performance.
    """
    from utils.features import build_features
    
    scored_variants = []
    for v in variants:
        # Build features for the predictor
        input_data = build_features(
            duration=v.get('suggested_duration_seconds', 60),
            title=v.get('content', '')[:100], # Use first 100 chars as title proxy
            hour=17, # Default to prime time
            weekend=False,
            df_silver=df_silver,
            platform_name=v['platform']
        )
        
        prediction = float(model.predict(input_data)[0])
        v['predicted_engagement'] = prediction
        scored_variants.append(v)
    
    return scored_variants