"""
INSTRUCTIONS: Updates needed for your existing models.py

This file shows the changes you need to make to your existing
backend/database/models.py file to add relationships for the fact checker.

These are ADDITIONS - don't delete anything, just add these lines.
"""

# ============================================================================
# STEP 1: Add import at the top of models.py
# ============================================================================
# 
# Find the imports section and add:
#
#     from backend.database.fact_check_models import ContentReview
#
# (This may not be necessary if you import the models elsewhere)


# ============================================================================
# STEP 2: Add relationship to Session class
# ============================================================================
#
# Find your Session class and add this line inside it:
#
#     # Fact check reviews linked to this session
#     content_reviews = relationship("ContentReview", back_populates="session")
#
# Example of where to add it:
#
#     class Session(Base):
#         __tablename__ = "sessions"
#         
#         id = Column(Integer, primary_key=True, index=True)
#         # ... other columns ...
#         
#         # Existing relationships
#         messages = relationship("Message", back_populates="session")
#         # ... other relationships ...
#         
#         # ADD THIS LINE:
#         content_reviews = relationship("ContentReview", back_populates="session")


# ============================================================================
# STEP 3: Add relationship to Project class
# ============================================================================
#
# Find your Project class and add this line inside it:
#
#     # Fact check reviews in this project
#     content_reviews = relationship("ContentReview", back_populates="project")
#
# Example:
#
#     class Project(Base):
#         __tablename__ = "projects"
#         
#         id = Column(Integer, primary_key=True, index=True)
#         # ... other columns ...
#         
#         # ADD THIS LINE:
#         content_reviews = relationship("ContentReview", back_populates="project")


# ============================================================================
# STEP 4: Add relationship to User class
# ============================================================================
#
# Find your User class and add this line inside it:
#
#     # Fact check reviews created by this user
#     content_reviews = relationship("ContentReview", back_populates="user")
#
# Example:
#
#     class User(Base):
#         __tablename__ = "users"
#         
#         id = Column(Integer, primary_key=True, index=True)
#         # ... other columns ...
#         
#         # ADD THIS LINE:
#         content_reviews = relationship("ContentReview", back_populates="user")


# ============================================================================
# THAT'S IT!
# ============================================================================
#
# After making these changes:
#
# 1. Save models.py
# 2. Run the migration:
#    
#    python -m backend.database.migrations.create_fact_check_tables
#
# 3. Verify the tables were created by checking your database
#
# ============================================================================
