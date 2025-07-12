#!/usr/bin/env python3
"""
Test script to generate a large file for testing advanced loading functionality.
This will create a file with more than 1000 lines to trigger the advanced loading system.
"""

import os
import json
import random
import string

def generate_large_text_file(filename="large_test_file.txt", num_lines=1500):
    """Generate a large text file with the specified number of lines"""
    print(f"Generating {num_lines} lines in {filename}...")
    
    with open(filename, 'w', encoding='utf-8') as f:
        for i in range(num_lines):
            # Generate some varied content
            if i % 100 == 0:
                f.write(f"# Section {i//100 + 1} - This is a comment line\n")
            elif i % 50 == 0:
                f.write(f"// Another comment style at line {i+1}\n")
            elif i % 25 == 0:
                f.write(f"/* Multi-line comment block starting at line {i+1} */\n")
            else:
                # Generate random content
                line_type = random.choice(['code', 'data', 'text'])
                if line_type == 'code':
                    f.write(f"def function_{i}():\n")
                    f.write(f"    return 'result_{i}'\n")
                elif line_type == 'data':
                    f.write(f"data_{i} = {random.randint(1, 1000)}\n")
                else:
                    # Generate random text
                    words = random.randint(3, 8)
                    text = ' '.join([''.join(random.choices(string.ascii_lowercase, k=random.randint(3, 8))) for _ in range(words)])
                    f.write(f"Line {i+1}: {text}\n")
    
    print(f"Generated {filename} with {num_lines} lines")

def generate_large_json_file(filename="large_test_data.json", num_objects=1000):
    """Generate a large JSON file with the specified number of objects"""
    print(f"Generating {num_objects} JSON objects in {filename}...")
    
    data = []
    for i in range(num_objects):
        obj = {
            "id": i,
            "name": f"Item_{i}",
            "description": f"This is item number {i} with some description text",
            "value": random.randint(1, 10000),
            "tags": [f"tag_{j}" for j in range(random.randint(1, 5))],
            "metadata": {
                "created": f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
                "category": random.choice(["A", "B", "C", "D"]),
                "priority": random.randint(1, 10)
            }
        }
        data.append(obj)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print(f"Generated {filename} with {num_objects} objects")

def generate_large_csv_file(filename="large_test_data.csv", num_rows=2000):
    """Generate a large CSV file with the specified number of rows"""
    print(f"Generating {num_rows} CSV rows in {filename}...")
    
    with open(filename, 'w', encoding='utf-8') as f:
        # Write header
        f.write("ID,Name,Email,Age,City,Salary,Department,JoinDate\n")
        
        # Write data rows
        for i in range(num_rows):
            name = f"User_{i}"
            email = f"user{i}@example.com"
            age = random.randint(18, 65)
            city = random.choice(["New York", "London", "Tokyo", "Paris", "Berlin", "Sydney"])
            salary = random.randint(30000, 150000)
            department = random.choice(["Engineering", "Sales", "Marketing", "HR", "Finance"])
            join_date = f"202{random.randint(0, 3)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
            
            f.write(f"{i},{name},{email},{age},{city},{salary},{department},{join_date}\n")
    
    print(f"Generated {filename} with {num_rows} rows")

def main():
    """Generate test files for advanced loading testing"""
    print("Generating test files for advanced loading functionality...")
    print("=" * 60)
    
    # Generate different types of large files
    generate_large_text_file("large_test_file.txt", 1500)
    generate_large_json_file("large_test_data.json", 1000)
    generate_large_csv_file("large_test_data.csv", 2000)
    
    print("\n" + "=" * 60)
    print("Test files generated successfully!")
    print("You can now test the advanced loading functionality by:")
    print("1. Opening these files in the editor")
    print("2. Using Tools -> Open Large File (Advanced Loading)")
    print("3. The files should trigger the advanced loading dialog")

if __name__ == "__main__":
    main() 