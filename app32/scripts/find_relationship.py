import sys
import os
sys.path.insert(0, os.getcwd())
from models import db
from app import app
from sqlalchemy import inspect

with app.app_context():
    print("Checking relationships...")
    
    # Iterate over all models in the registry
    for name, mapper in db.Model.registry.mappers.items():
        # mapper is the class-level mapper
        for prop in mapper.iterate_properties:
            # Check if it's a relationship
            if hasattr(prop, 'direction'):
                # Check if it points to Company
                if prop.mapper.class_.__name__ == 'Company':
                    backref = getattr(prop, 'back_populates', None) or getattr(prop, 'backref', None)
                    print(f"Model: {mapper.class_.__name__}, Property: {prop.key}, Points to: Company, Backref/Populates: {backref}")
                
                # Also check the other way around: Does any model define a relationship on Company?
                # Actually, backrefs are added to the target model.
