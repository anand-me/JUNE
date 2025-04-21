import datetime
from .policy import Policy, PolicyCollection
from june.interaction import Interaction
from collections import defaultdict
import random  # Added for random number generation

class InteractionPolicy(Policy):
    policy_type = "interaction"

class InteractionPolicies(PolicyCollection):
    policy_type = "interaction"
    
    def apply(self, date: datetime, interaction: Interaction):
        active_policies = self.get_active(date)
        beta_reductions = defaultdict(lambda: 1.0)
        for policy in active_policies:
            beta_reductions_dict = policy.apply()
            for group in beta_reductions_dict:
                beta_reductions[group] *= beta_reductions_dict[group]
        interaction.beta_reductions = beta_reductions

class SocialDistancing(InteractionPolicy):
    policy_subtype = "beta_factor"
    
    def __init__(self, start_time: str, end_time: str, beta_factors: dict = None):
        super().__init__(start_time, end_time)
        self.beta_factors = beta_factors
    
    def apply(self):
        """
        Implement social distancing policy
        
        -----------
        Parameters:
        betas: e.g. (dict) from DefaultInteraction, e.g. DefaultInteraction.from_file(selector=selector).beta
        
        Assumptions:
        - Currently we assume that social distancing is implemented first and this affects all
          interactions and intensities globally
        - Currently we assume that the changes are not group dependent
        
        TODO:
        - Implement structure for people to adhere to social distancing with a certain compliance
        - Check per group in config file
        """
        return self.beta_factors

class MaskWearing(InteractionPolicy):
    policy_subtype = "beta_factor"
    
    def __init__(
        self,
        start_time: str,
        end_time: str,
        compliance: float,
        beta_factor: float,
        beta_factor_male: float = None,  # Added male-specific factor
        beta_factor_female: float = None,  # Added female-specific factor
        mask_probabilities: dict = None,
        behavioral_model: bool = False, 
    ):
        super().__init__(start_time, end_time)
        self.compliance = compliance
        self.beta_factor = beta_factor
        # Use default if specific factors aren't provided
        self.beta_factor_male = beta_factor_male if beta_factor_male is not None else beta_factor
        self.beta_factor_female = beta_factor_female if beta_factor_female is not None else beta_factor
        self.mask_probabilities = mask_probabilities
        self.behavioral_model = behavioral_model
# Behavioral model parameters (based on Anderson's paper)
        self.odds_ratios = {
            "male": 0.437807,
            "white": 0.288743,
            "income_high": 2.470556,
            "democratic": 2.452319,
            "vulnerability_high": 3.571090,
            "intercept": 4.540417
        }

    
    def calculate_mask_adoption_probability(self, person):
        """
        Calculate the probability that an agent will adopt mask wearing
        based on their characteristics and perceived vulnerability.
        Based on Anderson et al. framework.
        """
        if not self.behavioral_model:
            return self.compliance  # Use standard compliance if not using behavioral model
        
        # Start with intercept
        odds = self.odds_ratios["intercept"]
        
        # Apply person characteristics
        if hasattr(person, "sex") and person.sex == "m":
            odds *= self.odds_ratios["male"]
        
        if hasattr(person, "ethnicity") and person.ethnicity == "white":
            odds *= self.odds_ratios["white"]
        
        if hasattr(person, "income") and person.income > 70000:
            odds *= self.odds_ratios["income_high"]
        
        if hasattr(person, "political") and person.political == "democratic":
            odds *= self.odds_ratios["democratic"]
        
        if hasattr(person, "perceived_vulnerability") and person.perceived_vulnerability:
            odds *= self.odds_ratios["vulnerability_high"]
        
        # Calculate probability
        probability = odds / (1 + odds)
        return probability	
        
    def apply(self):
        """
        Implement mask wearing policy
        
        -----------
        Parameters:
        betas: e.g. (dict) from DefaultInteraction, e.g. DefaultInteraction.from_file(selector=selector).beta
        
        Assumptions:
        - Currently we assume that mask wearing is implemented in a similar way to social distancing
          but with a mean field effect in beta reduction
        - Currently we assume that the changes are group dependent
        - The beta_factor is now demographic-specific (male/female)
        """
        ret = {}
        for key, value in self.mask_probabilities.items():
            # For now, use the default beta_factor as we modify the person-specific values elsewhere
            ret[key] = 1 - (value * self.compliance * (1 - self.beta_factor))
        return ret
    
    def apply_to_person(self, person):
        """
        Apply mask wearing based on person's demographics
        
        This method should be called for each person when processing interactions
        """
        if random.random() < self.compliance:
            person.mask_wearing = True
            
            # Apply gender-specific mask factor
            if hasattr(person, 'sex'):
                if person.sex == "m":
                    person.mask_factor = self.beta_factor_male
                elif person.sex == "f":
                    person.mask_factor = self.beta_factor_female
                else:
                    person.mask_factor = self.beta_factor
            else:
                person.mask_factor = self.beta_factor
        else:
            person.mask_wearing = False
            person.mask_factor = 1.0  # No reduction