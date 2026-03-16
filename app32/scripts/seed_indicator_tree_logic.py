
import os, sys
sys.path.append(os.getcwd())
from app import create_app
from models import db, IncentiveIndicator, IncentiveIndicatorTree, Company

app = create_app()
with app.app_context():
    companies = Company.query.all()
    
    for co in companies:
        print(f"Processing Company: {co.name} ({co.client_code})")
        
        # 1. Create Base Tree Nodes
        # Level 1: Operacional (code: 1)
        # Level 2: Financeiro (code: 2)
        # Level 3: Comportamental (code: 3)
        
        tree_mapping = {
            "1": "Operacional",
            "2": "Financeiro",
            "3": "Comportamental"
        }
        
        nodes = {}
        for code, name in tree_mapping.items():
            node = IncentiveIndicatorTree.query.filter_by(company_id=co.id, code=code).first()
            if not node:
                node = IncentiveIndicatorTree(company_id=co.id, code=code, name=name)
                db.session.add(node)
                db.session.flush()
                print(f"  Created tree node: {name}")
            nodes[code] = node
            
        # 2. Update existing indicators
        # Assign all to "Operacional" as default for now
        indicators = IncentiveIndicator.query.filter_by(company_id=co.id).all()
        idx = 1
        for ind in indicators:
            if not ind.tree_id:
                ind.tree_id = nodes["1"].id
            
            # Generate Full Code: {CompanyCode}.I.{TreeCode}.{IndicatorID}
            # Note: IndicatorID in DB is unique but for the display code we can use the ID or a sequence
            prefix = co.client_code if co.client_code else "CO"
            tree_code = nodes["1"].code # Since we assigned all to 1
            ind.full_code = f"{prefix}.I.{tree_code}.{ind.id}"
            print(f"  Updated indicator: {ind.name} -> {ind.full_code}")
            idx += 1
            
    db.session.commit()
    print("Seeding and migration completed.")
