# Sunflower AI Modelfiles

**The Intelligence Core of Sunflower AI**

This directory contains the Modelfiles that define the behavior, personality, and educational capabilities of Sunflower AI. These files represent 90% of the system's intelligence and are carefully crafted to provide safe, age-appropriate STEM education.

## 🌻 Overview

Sunflower AI uses two specialized AI models:

1. **Sunflower AI Kids** - The primary interface for children (ages 2-18)
2. **Sunflower AI Educator** - The professional interface for parents and teachers

Both models are built on top of open-source language models (Llama) and enhanced with extensive custom prompting to create a safe, educational experience.

## 📚 Model Architecture

### Sunflower AI Kids (Primary Model)
**File**: `Sunflower_AI_Kids.modelfile`

This model embodies a Mary Poppins-inspired personality - warm, knowledgeable, and magical in making learning fun. Key features:

- **Age-Adaptive Responses**: Automatically adjusts vocabulary, complexity, and length based on child's age
- **Built-in Safety**: Three-strike system for inappropriate requests with parent notifications
- **STEM Focus**: Comprehensive knowledge across all STEM subjects
- **Memory System**: Tracks learning progress, interests, and vocabulary for each child
- **Educational Scaffolding**: Builds on previous knowledge and gently corrects misconceptions

#### Age Adaptation Guidelines
- **Ages 2-5**: 30-50 words, concrete concepts, sensory descriptions
- **Ages 6-8**: 50-75 words, cause-and-effect, gentle vocabulary building  
- **Ages 9-12**: 75-100 words, abstract thinking, scientific method
- **Ages 13-16**: 100-200 words, critical thinking, multiple perspectives
- **Ages 17-18**: 200-300 words, college prep, career connections

### Sunflower AI Educator (Parent/Teacher Model)
**File**: `Sunflower_AI_Educator.modelfile`

Professional assistant for adults supporting children's STEM education:

- **Lesson Planning**: Complete curriculum development with standards alignment
- **Progress Analysis**: Interprets children's learning patterns and suggests next steps
- **Resource Creation**: Generates worksheets, activities, and assessments
- **Multi-Child Support**: Handles differentiated instruction for multiple children
- **Safety Reporting**: Detailed incident reports and intervention suggestions

## 🚀 Setup Instructions

### Prerequisites
1. Install Ollama: https://ollama.ai
2. Ensure you have at least 4GB RAM available
3. Close unnecessary applications for best performance

### Quick Setup
```bash
# Navigate to modelfiles directory
cd modelfiles

# Run the setup script
python setup_models.py
```

### Manual Setup
If the automated setup fails, you can create models manually:

```bash
# Create the Kids model
ollama create sunflower-kids -f Sunflower_AI_Kids.modelfile

# Create the Educator model  
ollama create sunflower-educator -f Sunflower_AI_Educator.modelfile

# Verify installation
ollama list
```

### Model Sizes and Options

The Modelfiles are configured to use `llama3.2:3b` by default, which provides the best balance of quality and performance. However, you can modify the base model based on your hardware:

#### Recommended Models by RAM:
- **4-6GB RAM**: Use `llama3.2:1b` or `llama3.2:1b-q4_0` (quantized)
- **8-12GB RAM**: Use `llama3.2:3b` (default)
- **16GB+ RAM**: Use `llama3.1:8b` for enhanced quality
- **32GB+ RAM**: Use `llama3.1:70b` for best possible responses

To change the base model, edit the first line of the Modelfile:
```
FROM llama3.2:1b  # For low-memory systems
```

## 🔧 Customization

### Adjusting Response Length
You can modify the age-based response lengths by editing the word count ranges in the SYSTEM prompt. Look for sections like:
```
Ages 2-5: Use 30-50 words with simple, concrete language...
```

### Adding Custom Knowledge
To add specific educational content or local curriculum requirements, you can append to the SYSTEM prompt:
```
Additionally, focus on these local science topics:
- Regional flora and fauna specific to [your area]
- Local weather patterns and climate
- [Your state's] geological features
```

### Modifying Safety Thresholds
The three-strike system can be adjusted by modifying the ENHANCED SAFETY PROTOCOL section. You can make it more or less strict based on your family's needs.

## 🧪 Testing Models

### Basic Functionality Test
```bash
# Test the Kids model
python safety_testing.py

# This will run comprehensive safety tests including:
# - Age-appropriate responses
# - Safety redirections
# - Vocabulary adaptation
# - Educational content delivery
```

### Manual Testing
```bash
# Test Kids model directly
ollama run sunflower-kids "I'm 8 years old. Why do leaves change color?"

# Test Educator model
ollama run sunflower-educator "Create a lesson plan about photosynthesis for a 10-year-old"
```

### Integration Testing
```bash
# Test profile integration
python profile_integration_example.py

# This demonstrates how the models integrate with:
# - Child profiles
# - Session logging
# - Progress tracking
# - Parent reporting
```

## 📊 Performance Optimization

### Model Parameters
The Modelfiles include these optimization parameters:
- **temperature**: 0.8 (Kids) / 0.7 (Educator) - Controls creativity vs consistency
- **top_p**: 0.9 - Nucleus sampling for natural responses
- **repeat_penalty**: 1.1 - Reduces repetitive output

### Hardware-Specific Tuning
The system automatically detects your hardware and adjusts:
- Context window size (based on RAM)
- GPU acceleration (if available)
- Thread count (based on CPU cores)

To manually override, add parameters:
```
PARAMETER num_ctx 2048      # Smaller context for low RAM
PARAMETER num_thread 4      # Limit CPU threads
PARAMETER num_gpu 0         # Disable GPU
```

## 🔒 Safety Features

### Kids Model Safety
1. **Content Filtering**: All inappropriate topics redirect to safe STEM alternatives
2. **Age Verification**: Responses match profile age, not stated age
3. **Parent Alerts**: Automatic logging of concerning interactions
4. **Strike System**: Progressive responses to repeated inappropriate requests

### Educator Model Safety
1. **Password Protection**: Parent dashboard requires authentication
2. **Full Transparency**: Complete access to all child interactions
3. **No Filtering**: Adults get unfiltered educational content
4. **Incident Analysis**: Detailed breakdowns of safety events

## 🌟 Educational Philosophy

### Learning Principles Embedded in Models

1. **Constructivism**: Build on existing knowledge
2. **Scaffolding**: Progressive complexity increase
3. **Multiple Intelligences**: Visual, auditory, kinesthetic approaches
4. **Growth Mindset**: Praise effort and curiosity
5. **Inquiry-Based**: Encourage questions and exploration

### STEM Coverage

#### Science
- Life Science: Biology, ecology, anatomy
- Physical Science: Physics, chemistry
- Earth & Space: Geology, astronomy, weather
- Scientific Method: Observation, hypothesis, experimentation

#### Technology
- Computer Science: Basic programming concepts
- Digital Literacy: Safe internet use, research skills
- Engineering Tools: CAD concepts, 3D printing basics

#### Engineering
- Design Process: Problem → Solution iteration
- Systems Thinking: How parts work together
- Materials Science: Properties and applications

#### Mathematics
- Number Sense: Age-appropriate arithmetic through calculus
- Geometry: Shapes through trigonometry
- Data & Statistics: Collection, analysis, interpretation
- Applied Math: Real-world problem solving

## 📈 Continuous Improvement

### Monitoring Model Performance
The system tracks:
- Response times per hardware configuration
- Safety incident rates by age group
- Learning outcome improvements
- Parent satisfaction metrics

### Updating Models
When Ollama releases new base models:
1. Test thoroughly with `safety_testing.py`
2. Verify age-appropriate responses
3. Check safety feature functionality
4. Validate educational content accuracy

### Version Control
Each Modelfile includes version information. When making changes:
1. Increment version number
2. Document changes in this README
3. Test extensively before deployment
4. Keep previous versions for rollback

## 🆘 Troubleshooting

### Common Issues

**Model Not Found**
```bash
Error: model 'sunflower-kids' not found
```
Solution: Run `python setup_models.py` or create manually

**Slow Responses**
- Close other applications
- Use a smaller base model
- Check available RAM
- Consider upgrading hardware

**Inappropriate Responses**
- Verify latest Modelfile is loaded
- Check child's age setting
- Review safety test results
- Report issue for investigation

**Connection Errors**
```bash
Error: could not connect to ollama
```
Solution: Ensure Ollama is running with `ollama serve`

### Getting Help
Since this is a zero-maintenance system:
1. First check this README
2. Run diagnostic tests
3. Review setup videos
4. Check printed documentation
5. Consider hardware limitations

## 🎯 Best Practices

### For Parents
1. Review session logs weekly
2. Discuss interesting topics with children
3. Celebrate learning milestones
4. Adjust settings as children grow

### For Developers
1. Test all changes with multiple age groups
2. Prioritize safety over features
3. Maintain educational focus
4. Document extensively

### For Educators
1. Align activities with curriculum standards
2. Use progress data for lesson planning
3. Encourage family participation
4. Share successful strategies

---

**Remember: These Modelfiles are the heart of Sunflower AI. They transform a general-purpose language model into a safe, educational companion for children. Handle with care and always prioritize child safety.**

**Version**: 1.0  
**Last Updated**: January 2025  
**Compatibility**: Ollama 0.1.29+
