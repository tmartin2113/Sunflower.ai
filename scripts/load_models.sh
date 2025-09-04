#!/bin/bash
# Sunflower AI Model Loading Script
# Automatically loads and configures AI models for the education system

set -e

echo "🌻 Sunflower AI Model Loader"
echo "============================"

# Configuration
OLLAMA_HOST="${OLLAMA_HOST:-http://ollama:11434}"
MAX_RETRIES=30
RETRY_DELAY=2

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if Ollama is ready
check_ollama() {
    echo -n "⏳ Waiting for Ollama service..."
    for i in $(seq 1 $MAX_RETRIES); do
        if curl -s "${OLLAMA_HOST}/api/tags" > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep $RETRY_DELAY
    done
    echo -e " ${RED}✗${NC}"
    echo "❌ Error: Ollama service not responding after ${MAX_RETRIES} attempts"
    exit 1
}

# Function to pull a model
pull_model() {
    local model=$1
    echo -n "📥 Pulling ${model}..."
    
    if curl -s -X POST "${OLLAMA_HOST}/api/pull" \
        -d "{\"name\": \"${model}\"}" \
        -H "Content-Type: application/json" > /dev/null 2>&1; then
        
        # Wait for pull to complete
        while true; do
            response=$(curl -s "${OLLAMA_HOST}/api/tags")
            if echo "$response" | grep -q "$model"; then
                echo -e " ${GREEN}✓${NC}"
                return 0
            fi
            echo -n "."
            sleep 2
        done
    else
        echo -e " ${RED}✗${NC}"
        echo "⚠️  Warning: Failed to pull ${model}"
        return 1
    fi
}

# Function to create a custom model
create_model() {
    local name=$1
    local modelfile=$2
    
    echo -n "🔧 Creating ${name}..."
    
    # Check if modelfile exists
    if [ ! -f "$modelfile" ]; then
        echo -e " ${YELLOW}⚠${NC} Modelfile not found, creating default..."
        create_default_modelfile "$name" "$modelfile"
    fi
    
    # Read modelfile content
    modelfile_content=$(cat "$modelfile")
    
    # Create the model via API
    if curl -s -X POST "${OLLAMA_HOST}/api/create" \
        -d "{\"name\": \"${name}\", \"modelfile\": $(echo "$modelfile_content" | jq -Rs .)}" \
        -H "Content-Type: application/json" > /dev/null 2>&1; then
        echo -e " ${GREEN}✓${NC}"
        return 0
    else
        echo -e " ${RED}✗${NC}"
        echo "⚠️  Warning: Failed to create ${name}"
        return 1
    fi
}

# Function to create default modelfile if missing
create_default_modelfile() {
    local name=$1
    local filepath=$2
    
    if [ "$name" == "sunflower-kids" ]; then
        cat > "$filepath" << 'EOF'
FROM llama3.2:1b

SYSTEM """
You are Sunflower AI Kids, a friendly and safe educational assistant for children aged 5-17.

SAFETY RULES (HIGHEST PRIORITY):
- NEVER discuss violence, weapons, drugs, or inappropriate content
- If asked about unsafe topics, redirect to educational STEM content
- Always maintain age-appropriate language and complexity
- Monitor for concerning patterns and flag for parent review

AGE ADAPTATION:
- Ages 5-7: Use 30-50 words, simple language, concrete examples
- Ages 8-10: Use 50-75 words, introduce basic concepts
- Ages 11-13: Use 75-125 words, explore abstract ideas
- Ages 14-17: Use 125-200 words, discuss complex topics

EDUCATIONAL FOCUS:
- Science: Biology, Chemistry, Physics, Earth Science
- Technology: Computer basics, Digital literacy, Coding concepts
- Engineering: Design thinking, Problem solving, Building
- Mathematics: Age-appropriate math from counting to calculus

INTERACTION STYLE:
- Be encouraging and patient
- Use emoji sparingly for younger children
- Celebrate learning and curiosity
- Provide examples from everyday life
- Ask follow-up questions to encourage exploration

Remember: You are helping children learn and grow safely!
"""

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
EOF
    elif [ "$name" == "sunflower-educator" ]; then
        cat > "$filepath" << 'EOF'
FROM llama3.2:3b

SYSTEM """
You are Sunflower AI Educator, a professional educational assistant for parents and teachers.

PROFESSIONAL CAPABILITIES:
- Full access to all STEM topics without content restrictions
- Advanced explanations for adult comprehension
- Curriculum planning and lesson development
- Student progress analysis and reporting
- Educational resource recommendations

COMMUNICATION STYLE:
- Professional and informative
- Detailed explanations with pedagogical context
- Evidence-based educational strategies
- Clear and structured responses
- Support for differentiated instruction

PARENT DASHBOARD FEATURES:
- Summarize child learning sessions
- Identify areas of strength and improvement
- Suggest supplementary activities
- Flag any concerning interactions
- Provide age-appropriate learning recommendations

EDUCATOR SUPPORT:
- Lesson plan templates
- Assessment strategies
- STEM activity suggestions
- Cross-curricular connections
- Standards alignment guidance

Focus on empowering adults to support children's STEM education effectively.
"""

PARAMETER temperature 0.8
PARAMETER top_p 0.95
PARAMETER repeat_penalty 1.05
EOF
    fi
}

# Function to verify model exists
verify_model() {
    local model=$1
    echo -n "✅ Verifying ${model}..."
    
    response=$(curl -s "${OLLAMA_HOST}/api/tags")
    if echo "$response" | grep -q "$model"; then
        echo -e " ${GREEN}✓${NC}"
        return 0
    else
        echo -e " ${RED}✗${NC}"
        return 1
    fi
}

# Function to test a model
test_model() {
    local model=$1
    local prompt=$2
    
    echo -n "🧪 Testing ${model}..."
    
    response=$(curl -s -X POST "${OLLAMA_HOST}/api/generate" \
        -d "{\"model\": \"${model}\", \"prompt\": \"${prompt}\", \"stream\": false}" \
        -H "Content-Type: application/json" \
        --max-time 30)
    
    if echo "$response" | grep -q "response"; then
        echo -e " ${GREEN}✓${NC}"
        # Extract and show first 100 chars of response
        response_text=$(echo "$response" | jq -r '.response' | head -c 100)
        echo "   Response: ${response_text}..."
        return 0
    else
        echo -e " ${RED}✗${NC}"
        return 1
    fi
}

# Main execution
main() {
    echo "🚀 Starting model initialization..."
    echo ""
    
    # Step 1: Check Ollama connectivity
    check_ollama
    
    # Step 2: List existing models
    echo "📋 Checking existing models..."
    existing_models=$(curl -s "${OLLAMA_HOST}/api/tags" | jq -r '.models[]?.name // empty')
    if [ -n "$existing_models" ]; then
        echo "   Found models:"
        echo "$existing_models" | while read -r model; do
            echo "   - $model"
        done
    else
        echo "   No existing models found"
    fi
    echo ""
    
    # Step 3: Pull base models
    echo "📦 Downloading base models..."
    
    # Determine which models to pull based on available memory
    AVAILABLE_MEMORY=$(free -g | awk '/^Mem:/{print $7}')
    
    if [ "$AVAILABLE_MEMORY" -ge 16 ]; then
        echo "   High memory detected (${AVAILABLE_MEMORY}GB) - using large models"
        BASE_KIDS_MODEL="llama3.2:3b"
        BASE_EDUCATOR_MODEL="llama3.2:7b"
    elif [ "$AVAILABLE_MEMORY" -ge 8 ]; then
        echo "   Medium memory detected (${AVAILABLE_MEMORY}GB) - using medium models"
        BASE_KIDS_MODEL="llama3.2:1b"
        BASE_EDUCATOR_MODEL="llama3.2:3b"
    else
        echo "   Low memory detected (${AVAILABLE_MEMORY}GB) - using small models"
        BASE_KIDS_MODEL="llama3.2:1b"
        BASE_EDUCATOR_MODEL="llama3.2:1b"
    fi
    
    pull_model "$BASE_KIDS_MODEL"
    pull_model "$BASE_EDUCATOR_MODEL"
    echo ""
    
    # Step 4: Create Sunflower models
    echo "🌻 Creating Sunflower models..."
    
    # Update modelfiles with correct base models
    if [ -f "/models/sunflower-kids.modelfile" ]; then
        sed -i "s/FROM .*/FROM ${BASE_KIDS_MODEL}/" "/models/sunflower-kids.modelfile"
    fi
    
    if [ -f "/models/sunflower-educator.modelfile" ]; then
        sed -i "s/FROM .*/FROM ${BASE_EDUCATOR_MODEL}/" "/models/sunflower-educator.modelfile"
    fi
    
    create_model "sunflower-kids" "/models/sunflower-kids.modelfile"
    create_model "sunflower-educator" "/models/sunflower-educator.modelfile"
    echo ""
    
    # Step 5: Verify models
    echo "🔍 Verifying models..."
    verify_model "sunflower-kids"
    verify_model "sunflower-educator"
    echo ""
    
    # Step 6: Test models
    echo "🧪 Running model tests..."
    test_model "sunflower-kids" "What is a rainbow? (I am 7 years old)"
    test_model "sunflower-educator" "How can I teach fractions to 4th graders?"
    echo ""
    
    # Step 7: Create optimized versions for different hardware
    echo "⚙️  Creating hardware-optimized variants..."
    
    # Create quantized version for low-end hardware
    echo -n "   Creating sunflower-kids-small..."
    cat > /tmp/kids-small.modelfile << EOF
FROM ${BASE_KIDS_MODEL}

SYSTEM """Sunflower AI Kids - Optimized for performance. Educational assistant for children."""

PARAMETER temperature 0.7
PARAMETER num_ctx 2048
PARAMETER num_thread 4
EOF
    
    if create_model "sunflower-kids-small" "/tmp/kids-small.modelfile"; then
        echo -e " ${GREEN}✓${NC}"
    fi
    
    echo ""
    echo "✨ Model initialization complete!"
    echo ""
    echo "📊 Summary:"
    echo "   Base models: ${BASE_KIDS_MODEL}, ${BASE_EDUCATOR_MODEL}"
    echo "   Custom models: sunflower-kids, sunflower-educator"
    echo "   Optimized variants: sunflower-kids-small"
    echo ""
    echo "🌻 Sunflower AI is ready for use!"
    
    # Keep container running for model-loader service
    if [ "$1" == "--keep-alive" ]; then
        echo "Container will stay alive for debugging..."
        tail -f /dev/null
    fi
}

# Error handling
trap 'echo -e "\n${RED}Error occurred during model loading${NC}"; exit 1' ERR

# Run main function
main "$@"
