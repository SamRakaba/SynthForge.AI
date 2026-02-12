#!/usr/bin/env python3
"""Analyze agent instruction files for wordiness, duplication, consistency, and hardcoded examples."""

import re
from pathlib import Path
from collections import Counter

def analyze_file(filepath):
    """Analyze a single instruction file."""
    with open(filepath, encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find all agents
    agents = []
    for i, line in enumerate(lines, 1):
        if re.match(r'^[a-z_]+_agent:', line):
            agent_name = line.strip().rstrip(':')
            agents.append({'name': agent_name, 'start': i, 'content_start': i})
    
    # Calculate line ranges
    results = []
    for i, agent in enumerate(agents):
        if i + 1 < len(agents):
            end_line = agents[i + 1]['start'] - 1
        else:
            end_line = len(lines)
        
        agent_lines = lines[agent['start']-1:end_line]
        agent_content = '\n'.join(agent_lines)
        
        # Analysis
        line_count = len(agent_lines)
        word_count = len(agent_content.split())
        
        # Find examples (json, code blocks, CORRECT/WRONG sections)
        example_lines = 0
        for line in agent_lines:
            if any(x in line.lower() for x in ['example', '```', 'correct:', 'wrong:', 'right:', 'incorrect:']):
                example_lines += 1
        
        # Find repeated phrases
        sentences = re.split(r'[.!?]\s+', agent_content)
        sentence_counts = Counter([s.strip().lower() for s in sentences if len(s.strip()) > 20])
        duplicates = [(s, c) for s, c in sentence_counts.items() if c > 1]
        
        # Find hardcoded lists
        hardcoded_patterns = [
            r'(Compute|Storage|Networking|Databases|AI \+ Machine Learning)',
            r'"(Azure [A-Z][^"]{10,})".*"(Azure [A-Z][^"]{10,})"',  # Multiple Azure service examples
            r'\b(example|Example|EXAMPLE)[:\s]',
        ]
        hardcoded_matches = []
        for pattern in hardcoded_patterns:
            matches = re.findall(pattern, agent_content, re.MULTILINE)
            if matches:
                hardcoded_matches.append(f"{len(matches)} matches for pattern")
        
        results.append({
            'name': agent['name'],
            'start': agent['start'],
            'end': end_line,
            'lines': line_count,
            'words': word_count,
            'example_lines': example_lines,
            'duplicates': len(duplicates),
            'hardcoded': len(hardcoded_matches),
            'top_duplicates': duplicates[:3] if duplicates else []
        })
    
    return results

def main():
    files = [
        ('synthforge/prompts/agent_instructions.yaml', 'PHASE 1 (Detection)'),
        ('synthforge/prompts/iac_agent_instructions.yaml', 'PHASE 2 (IaC Generation)'),
    ]
    
    print("\n" + "="*80)
    print("AGENT INSTRUCTION ANALYSIS")
    print("="*80)
    
    for filepath, phase_name in files:
        print(f"\n\n{'='*80}")
        print(f"{phase_name}: {filepath}")
        print("="*80)
        
        # File stats
        with open(filepath, encoding='utf-8') as f:
            total_lines = len(f.readlines())
        
        print(f"\nFile: {total_lines:,} total lines\n")
        
        # Agent stats
        agents = analyze_file(filepath)
        
        print(f"{'Agent':<35} {'Lines':>6} {'Words':>7} {'Examples':>9} {'Duplicates':>10} {'Hardcoded':>10}")
        print("-" * 80)
        
        for agent in agents:
            print(f"{agent['name']:<35} {agent['lines']:>6} {agent['words']:>7,} "
                  f"{agent['example_lines']:>9} {agent['duplicates']:>10} {agent['hardcoded']:>10}")
        
        # Summary
        total_lines_sum = sum(a['lines'] for a in agents)
        total_words_sum = sum(a['words'] for a in agents)
        total_examples = sum(a['example_lines'] for a in agents)
        
        print("-" * 80)
        print(f"{'TOTAL':<35} {total_lines_sum:>6} {total_words_sum:>7,} "
              f"{total_examples:>9} {sum(a['duplicates'] for a in agents):>10} "
              f"{sum(a['hardcoded'] for a in agents):>10}")
        
        # Detailed issues
        print(f"\n\n{'DETAILED ANALYSIS':^80}")
        print("=" * 80)
        
        for agent in agents:
            issues = []
            
            # Wordiness check
            if agent['words'] > 2000:
                issues.append(f"⚠️  VERY WORDY: {agent['words']:,} words (recommend < 2000)")
            elif agent['words'] > 1000:
                issues.append(f"⚠️  Wordy: {agent['words']:,} words (recommend < 1000)")
            
            # Example density
            example_pct = (agent['example_lines'] / agent['lines'] * 100) if agent['lines'] > 0 else 0
            if example_pct > 30:
                issues.append(f"⚠️  TOO MANY EXAMPLES: {example_pct:.1f}% of content is examples")
            
            # Duplicates
            if agent['duplicates'] > 3:
                issues.append(f"⚠️  DUPLICATION: {agent['duplicates']} repeated sentences found")
            
            # Hardcoded content
            if agent['hardcoded'] > 0:
                issues.append(f"⚠️  HARDCODED EXAMPLES: {agent['hardcoded']} patterns detected")
            
            if issues:
                print(f"\n{agent['name']}")
                print(f"  Lines {agent['start']}-{agent['end']} ({agent['lines']} lines, {agent['words']:,} words)")
                for issue in issues:
                    print(f"  {issue}")
        
        print("\n")

if __name__ == '__main__':
    main()
