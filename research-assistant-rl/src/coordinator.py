from src.agents import QueryStrategyAgent, SourceSelectorAgent
from src.synthesis import PaperSynthesizer
from collections import Counter


class EnhancedCoordinator:
    """
    Advanced coordinator with:
    - Dynamic task allocation
    - Agent voting mechanism
    - Fallback strategies
    - Communication protocols
    """
    
    def __init__(self):
        self.q_agent = QueryStrategyAgent()
        self.ucb_agent = SourceSelectorAgent()
        self.synthesizer = PaperSynthesizer()
        
        # Task allocation tracking
        self.task_allocation_history = {
            'q_agent': 0, 
            'ucb_agent': 0, 
            'both': 0
        }
    
    def allocate_task(self, task):
        """
        Dynamically decide which agents handle this task.
        Early: both agents learn. Later: specialize based on difficulty.
        """
        # Early episodes: both agents work on all tasks
        if self.q_agent.episode_count < 50:
            self.task_allocation_history['both'] += 1
            return 'both'
        
        # Later: specialize based on task difficulty
        if task.difficulty == 'easy':
            # UCB alone sufficient for easy tasks
            self.task_allocation_history['ucb_agent'] += 1
            return 'ucb_agent'
        elif task.difficulty == 'hard':
            # Q-Learning better for complex strategy decisions
            self.task_allocation_history['q_agent'] += 1
            return 'q_agent'
        else:
            # Both agents for medium difficulty
            self.task_allocation_history['both'] += 1
            return 'both'
    
    def agent_voting(self, state, topic):
        """
        Agents vote on source selection.
        Implements communication protocol between agents.
        """
        votes = {}
        
        # Q-agent's vote (based on learned Q-values)
        q_strategy, q_source = self.q_agent.choose_action(state)
        votes['q_agent'] = q_source
        
        # UCB agent's vote
        ucb_source = self.ucb_agent.choose_source(topic)
        votes['ucb_agent'] = ucb_source
        
        # Majority voting (communication protocol)
        vote_counts = Counter(votes.values())
        winning_source = vote_counts.most_common(1)[0][0]
        
        return winning_source, q_strategy, votes
    
    def research_with_fallback(self, env, task):
        """
        Execute research with comprehensive fallback strategy.
        
        Fallback chain:
        1. Try primary source
        2. If fails, try alternative source
        3. If still fails, return penalty
        """
        state = self.q_agent.get_state(task)
        
        # Dynamic task allocation
        allocation = self.allocate_task(task)
        
        # Decide strategy and source based on allocation
        if allocation == 'ucb_agent':
            # UCB only (for easy tasks)
            strategy = 'specific'  # Default strategy
            source = self.ucb_agent.choose_source(task.topic)
        elif allocation == 'q_agent':
            # Q-Learning only (for hard tasks)
            strategy, source = self.q_agent.choose_action(state)
        else:
            # Both agents: use voting (for medium tasks)
            source, strategy, votes = self.agent_voting(state, task.topic)
        
        # Execute search with fallback
        papers = None
        sources_tried = [source]
        
        try:
            papers, cost = env.execute_search(strategy, source)
            
            # Fallback if no papers retrieved
            if not papers or len(papers) == 0:
                raise ValueError("No papers retrieved")
                
        except Exception as e:
            # Fallback to alternative source
            backup_source = 'arxiv' if source == 'openalex' else 'openalex'
            sources_tried.append(backup_source)
            
            try:
                papers, cost = env.execute_search(strategy, backup_source)
                source = backup_source  # Update to actual source used
            except Exception:
                # Final fallback: return empty with penalty
                papers, cost = [], 5.0
        
        # Synthesize papers
        synthesis_result = self.synthesizer.synthesize(papers, task.query_terms)
        
        # Calculate reward
        if papers:
            base_reward = env.get_reward(papers, cost)
            synthesis_bonus = synthesis_result['quality'] * 2
            total_reward = base_reward + synthesis_bonus
        else:
            total_reward = -10  # Penalty for complete failure
        
        # Update agents based on allocation
        next_state = state
        if allocation in ['q_agent', 'both']:
            self.q_agent.update(state, (strategy, source), total_reward, next_state)
        if allocation in ['ucb_agent', 'both']:
            self.ucb_agent.update(task.topic, source, total_reward)
        
        return papers, total_reward, {
            'strategy': strategy,
            'source': source,
            'cost': cost,
            'relevance': task.evaluate_results(papers) if papers else 0,
            'papers_count': len(papers),
            'synthesis': synthesis_result['synthesis'],
            'synthesis_quality': synthesis_result['quality'],
            'new_terms': synthesis_result['new_terms_discovered'],
            'allocation': allocation,
            'sources_tried': sources_tried,
            'fallback_used': len(sources_tried) > 1
        }
