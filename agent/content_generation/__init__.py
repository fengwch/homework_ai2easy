# 内容生成：故事、插图提示、解题引导
from content_generation.story_generator.generator import generate_story
from content_generation.solution_generator.generator import generate_solution_guide
from content_generation.illustration_gen.prompts import generate_illustration_prompts

__all__ = ["generate_story", "generate_solution_guide", "generate_illustration_prompts"]
