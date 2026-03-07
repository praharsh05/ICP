
from fastapi import FastAPI, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Dict, Any
from sqlalchemy.orm import Session
import time

from app.db.postgres_client import init_db, get_db, engine
from app.models.user_db import UserDB
from app.routers import users, auth, user_management

app = FastAPI(title="FamilyTree API (Mock)", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Initialize PostgreSQL on startup
@app.on_event("startup")
def startup_event():
    try:
        init_db()
        print("✓ PostgreSQL database initialized")
    except Exception as e:
        print(f"⚠ Warning: Could not initialize PostgreSQL: {e}")

NOW = time.time()
MOCK_GRAPH = {
    # E1: Basic family - Single wife, multiple children
    "E1": {
        "root": "E1",
        "nodes": [
            {"id":"E1","label":"Ali Hassan","full_name":"Ali Hassan Al Mazrouei","name_eng":"Ali Hassan Al Mazrouei","name_arabic":"علي حسن المزروعي","dob":"1990-05-15","date_of_birth":"1990-05-15","unified_id":"E1","passport_no":"AE12345678","passport":"AE12345678","contact_no":"+971501234567","nationality":"UAE","gender":"M","sex":"M","national_id":"784-1990-1234567-1","kin":"self","person_type":"citizen"},
            {"id":"E2","label":"Hassan Ibrahim","full_name":"Hassan Ibrahim Al Mazrouei","name_eng":"Hassan Ibrahim Al Mazrouei","name_arabic":"حسن إبراهيم المزروعي","dob":"1965-03-20","date_of_birth":"1965-03-20","unified_id":"E2","passport_no":"AE87654321","passport":"AE87654321","contact_no":"+971502345678","nationality":"UAE","gender":"M","sex":"M","national_id":"784-1965-8765432-1","kin":"father","person_type":"citizen"},
            {"id":"E3","label":"Mariam Saeed","full_name":"Mariam Saeed Al Mansoori","name_eng":"Mariam Saeed Al Mansoori","name_arabic":"مريم سعيد المنصوري","dob":"1968-07-10","date_of_birth":"1968-07-10","unified_id":"E3","passport_no":"AE11223344","passport":"AE11223344","contact_no":"+971503456789","nationality":"UAE","gender":"F","sex":"F","national_id":"784-1968-1122334-2","kin":"mother","person_type":"citizen"},
            {"id":"E4","label":"Aisha Ali","full_name":"Aisha Ali Al Zaabi","name_eng":"Aisha Ali Al Zaabi","name_arabic":"عائشة علي الزعابي","dob":"1992-11-25","date_of_birth":"1992-11-25","unified_id":"E4","passport_no":"AE22334455","passport":"AE22334455","contact_no":"+971504567890","nationality":"UAE","gender":"F","sex":"F","national_id":"784-1992-2233445-2","kin":"wife","person_type":"citizen"},
            {"id":"E5","label":"Omar Ali","full_name":"Omar Ali Hassan","name_eng":"Omar Ali Hassan","name_arabic":"عمر علي حسن","dob":"2015-08-12","date_of_birth":"2015-08-12","unified_id":"E5","passport_no":"AE33445566","passport":"AE33445566","contact_no":"+971505678901","nationality":"UAE","gender":"M","sex":"M","national_id":"784-2015-3344556-1","kin":"son","person_type":"citizen"},
            {"id":"E6","label":"Laila Ali","full_name":"Laila Ali Hassan","name_eng":"Laila Ali Hassan","name_arabic":"ليلى علي حسن","dob":"2018-02-28","date_of_birth":"2018-02-28","unified_id":"E6","passport_no":"AE44556677","passport":"AE44556677","contact_no":"+971506789012","nationality":"UAE","gender":"F","sex":"F","national_id":"784-2018-4455667-2","kin":"daughter","person_type":"citizen"},
            {"id":"E7","label":"Fatima Hassan","full_name":"Fatima Hassan Al Mazrouei","name_eng":"Fatima Hassan Al Mazrouei","name_arabic":"فاطمة حسن المزروعي","dob":"1992-09-05","date_of_birth":"1992-09-05","unified_id":"E7","passport_no":"AE55667788","passport":"AE55667788","contact_no":"+971507890123","nationality":"UAE","gender":"F","sex":"F","national_id":"784-1992-5566778-2","kin":"sister","person_type":"citizen"}
        ],
        "edges": [
            {"source":"E1","target":"E2","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E1","target":"E3","type":"CHILD_OF","parent_sex":"F"},
            {"source":"E5","target":"E1","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E5","target":"E4","type":"CHILD_OF","parent_sex":"F"},
            {"source":"E6","target":"E1","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E6","target":"E4","type":"CHILD_OF","parent_sex":"F"},
            {"source":"E7","target":"E2","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E7","target":"E3","type":"CHILD_OF","parent_sex":"F"},
            {"source":"E1","target":"E4","type":"SPOUSE_OF","relationship_status":"active"},
            {"source":"E1","target":"E7","type":"SIBLING_OF"},
            {"source":"E5","target":"E6","type":"SIBLING_OF"}
        ],
        "generated_at": NOW
    },
    
    # E10: Multiple wives scenario - Polygamy with children from different mothers
    "E10": {
        "root": "E10",
        "nodes": [
            {"id":"E10","label":"Ahmed Khalid","full_name":"Ahmed Khalid Al Suwaidi","name_eng":"Ahmed Khalid Al Suwaidi","name_arabic":"أحمد خالد السويدي","dob":"1985-04-18","date_of_birth":"1985-04-18","unified_id":"E10","passport_no":"AE99887766","passport":"AE99887766","contact_no":"+971508901234","nationality":"UAE","gender":"M","sex":"M","national_id":"784-1985-9988776-1","kin":"self","person_type":"citizen"},
            {"id":"E11","label":"Khalid Mohammed","full_name":"Khalid Mohammed Al Suwaidi","name_eng":"Khalid Mohammed Al Suwaidi","name_arabic":"خالد محمد السويدي","dob":"1960-01-15","date_of_birth":"1960-01-15","unified_id":"E11","passport_no":"AE88776655","passport":"AE88776655","contact_no":"+971509012345","nationality":"UAE","gender":"M","sex":"M","national_id":"784-1960-8877665-1","kin":"father","person_type":"citizen"},
            {"id":"E12","label":"Salma Ahmed","full_name":"Salma Ahmed Al Nuaimi","name_eng":"Salma Ahmed Al Nuaimi","name_arabic":"سلمى أحمد النعيمي","dob":"1963-06-22","date_of_birth":"1963-06-22","unified_id":"E12","passport_no":"AE77665544","passport":"AE77665544","contact_no":"+971501012345","nationality":"UAE","gender":"F","sex":"F","national_id":"784-1963-7766554-2","kin":"mother","person_type":"citizen"},
            {"id":"E13","label":"Fatima Ahmed","full_name":"Fatima Ahmed Al Suwaidi","name_eng":"Fatima Ahmed Al Suwaidi","name_arabic":"فاطمة أحمد السويدي","dob":"1987-09-30","date_of_birth":"1987-09-30","unified_id":"E13","passport_no":"AE66554433","passport":"AE66554433","contact_no":"+971501123456","nationality":"UAE","gender":"F","sex":"F","national_id":"784-1987-6655443-2","kin":"wife","person_type":"citizen"},
            {"id":"E14","label":"Zainab Ahmed","full_name":"Zainab Ahmed Al Suwaidi","name_eng":"Zainab Ahmed Al Suwaidi","name_arabic":"زينب أحمد السويدي","dob":"1989-12-14","date_of_birth":"1989-12-14","unified_id":"E14","passport_no":"AE55443322","passport":"AE55443322","contact_no":"+971501234567","nationality":"UAE","gender":"F","sex":"F","national_id":"784-1989-5544332-2","kin":"wife","person_type":"citizen"},
            {"id":"E15","label":"Maryam Ahmed","full_name":"Maryam Ahmed Al Suwaidi","name_eng":"Maryam Ahmed Al Suwaidi","name_arabic":"مريم أحمد السويدي","dob":"1991-03-08","date_of_birth":"1991-03-08","unified_id":"E15","passport_no":"AE44332211","passport":"AE44332211","contact_no":"+971501345678","nationality":"UAE","gender":"F","sex":"F","national_id":"784-1991-4433221-2","kin":"wife","person_type":"citizen"},
            {"id":"E16","label":"Yusuf Ahmed","full_name":"Yusuf Ahmed Khalid","name_eng":"Yusuf Ahmed Khalid","name_arabic":"يوسف أحمد خالد","dob":"2010-07-20","date_of_birth":"2010-07-20","unified_id":"E16","passport_no":"AE33221100","passport":"AE33221100","contact_no":"+971501456789","nationality":"UAE","gender":"M","sex":"M","national_id":"784-2010-3322110-1","kin":"son","person_type":"citizen"},
            {"id":"E17","label":"Hassan Ahmed","full_name":"Hassan Ahmed Khalid","name_eng":"Hassan Ahmed Khalid","name_arabic":"حسن أحمد خالد","dob":"2012-11-05","date_of_birth":"2012-11-05","unified_id":"E17","passport_no":"AE22110099","passport":"AE22110099","contact_no":"+971501567890","nationality":"UAE","gender":"M","sex":"M","national_id":"784-2012-2211009-1","kin":"son","person_type":"citizen"},
            {"id":"E18","label":"Amina Ahmed","full_name":"Amina Ahmed Khalid","name_eng":"Amina Ahmed Khalid","name_arabic":"أمينة أحمد خالد","dob":"2014-02-18","date_of_birth":"2014-02-18","unified_id":"E18","passport_no":"AE11009988","passport":"AE11009988","contact_no":"+971501678901","nationality":"UAE","gender":"F","sex":"F","national_id":"784-2014-1100998-2","kin":"daughter","person_type":"citizen"},
            {"id":"E19","label":"Khadija Ahmed","full_name":"Khadija Ahmed Khalid","name_eng":"Khadija Ahmed Khalid","name_arabic":"خديجة أحمد خالد","dob":"2016-05-25","date_of_birth":"2016-05-25","unified_id":"E19","passport_no":"AE00998877","passport":"AE00998877","contact_no":"+971501789012","nationality":"UAE","gender":"F","sex":"F","national_id":"784-2016-0099887-2","kin":"daughter","person_type":"citizen"},
            {"id":"E20","label":"Ibrahim Ahmed","full_name":"Ibrahim Ahmed Khalid","name_eng":"Ibrahim Ahmed Khalid","name_arabic":"إبراهيم أحمد خالد","dob":"2018-08-10","date_of_birth":"2018-08-10","unified_id":"E20","passport_no":"AE99887766","passport":"AE99887766","contact_no":"+971501890123","nationality":"UAE","gender":"M","sex":"M","national_id":"784-2018-9988776-1","kin":"son","person_type":"citizen"},
            {"id":"E21","label":"Sara Ahmed","full_name":"Sara Ahmed Khalid","name_eng":"Sara Ahmed Khalid","name_arabic":"سارة أحمد خالد","dob":"2020-10-15","date_of_birth":"2020-10-15","unified_id":"E21","passport_no":"AE88776655","passport":"AE88776655","contact_no":"+971501901234","nationality":"UAE","gender":"F","sex":"F","national_id":"784-2020-8877665-2","kin":"daughter","person_type":"citizen"}
        ],
        "edges": [
            {"source":"E10","target":"E11","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E10","target":"E12","type":"CHILD_OF","parent_sex":"F"},
            # First wife - Fatima (E13) - has 2 children
            {"source":"E16","target":"E10","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E16","target":"E13","type":"CHILD_OF","parent_sex":"F"},
            {"source":"E17","target":"E10","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E17","target":"E13","type":"CHILD_OF","parent_sex":"F"},
            # Second wife - Zainab (E14) - has 2 children
            {"source":"E18","target":"E10","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E18","target":"E14","type":"CHILD_OF","parent_sex":"F"},
            {"source":"E19","target":"E10","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E19","target":"E14","type":"CHILD_OF","parent_sex":"F"},
            # Third wife - Maryam (E15) - has 2 children
            {"source":"E20","target":"E10","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E20","target":"E15","type":"CHILD_OF","parent_sex":"F"},
            {"source":"E21","target":"E10","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E21","target":"E15","type":"CHILD_OF","parent_sex":"F"},
            # Spouse relationships
            {"source":"E10","target":"E13","type":"SPOUSE_OF","relationship_status":"active"},
            {"source":"E10","target":"E14","type":"SPOUSE_OF","relationship_status":"active"},
            {"source":"E10","target":"E15","type":"SPOUSE_OF","relationship_status":"active"},
            # Sibling relationships (children from same mother)
            {"source":"E16","target":"E17","type":"SIBLING_OF"},
            {"source":"E18","target":"E19","type":"SIBLING_OF"},
            {"source":"E20","target":"E21","type":"SIBLING_OF"}
        ],
        "generated_at": NOW
    },
    
    # E20: Divorced spouse scenario - Clear parentage
    "E20": {
        "root": "E20",
        "nodes": [
            {"id":"E20","label":"Mohammed Ali","full_name":"Mohammed Ali Al Dhaheri","name_eng":"Mohammed Ali Al Dhaheri","name_arabic":"محمد علي الظاهري","dob":"1988-06-12","date_of_birth":"1988-06-12","unified_id":"E20","passport_no":"AE77665544","passport":"AE77665544","contact_no":"+971502012345","nationality":"UAE","gender":"M","sex":"M","national_id":"784-1988-7766554-1","kin":"self","person_type":"citizen"},
            {"id":"E21","label":"Ali Hassan","full_name":"Ali Hassan Al Dhaheri","name_eng":"Ali Hassan Al Dhaheri","name_arabic":"علي حسن الظاهري","dob":"1962-09-25","date_of_birth":"1962-09-25","unified_id":"E21","passport_no":"AE66554433","passport":"AE66554433","contact_no":"+971502123456","nationality":"UAE","gender":"M","sex":"M","national_id":"784-1962-6655443-1","kin":"father","person_type":"citizen"},
            {"id":"E22","label":"Noor Ali","full_name":"Noor Ali Al Dhaheri","name_eng":"Noor Ali Al Dhaheri","name_arabic":"نور علي الظاهري","dob":"1965-12-08","date_of_birth":"1965-12-08","unified_id":"E22","passport_no":"AE55443322","passport":"AE55443322","contact_no":"+971502234567","nationality":"UAE","gender":"F","sex":"F","national_id":"784-1965-5544332-2","kin":"mother","person_type":"citizen"},
            {"id":"E23","label":"Layla Mohammed","full_name":"Layla Mohammed Al Dhaheri","name_eng":"Layla Mohammed Al Dhaheri","name_arabic":"ليلى محمد الظاهري","dob":"1990-03-20","date_of_birth":"1990-03-20","unified_id":"E23","passport_no":"AE44332211","passport":"AE44332211","contact_no":"+971502345678","nationality":"UAE","gender":"F","sex":"F","national_id":"784-1990-4433221-2","kin":"wife","person_type":"citizen"},
            {"id":"E24","label":"Sana Mohammed","full_name":"Sana Mohammed Al Dhaheri","name_eng":"Sana Mohammed Al Dhaheri","name_arabic":"سناء محمد الظاهري","dob":"1992-07-14","date_of_birth":"1992-07-14","unified_id":"E24","passport_no":"AE33221100","passport":"AE33221100","contact_no":"+971502456789","nationality":"UAE","gender":"F","sex":"F","national_id":"784-1992-3322110-2","kin":"wife","person_type":"citizen"},
            # Children from divorced wife (E23 - Layla)
            {"id":"E25","label":"Omar Mohammed","full_name":"Omar Mohammed Ali (son of Layla)","name_eng":"Omar Mohammed Ali","name_arabic":"عمر محمد علي","dob":"2012-04-30","date_of_birth":"2012-04-30","unified_id":"E25","passport_no":"AE22110099","passport":"AE22110099","contact_no":"+971502567890","nationality":"UAE","gender":"M","sex":"M","national_id":"784-2012-2211009-1","kin":"son","person_type":"citizen"},
            {"id":"E26","label":"Huda Mohammed","full_name":"Huda Mohammed Ali (daughter of Layla)","name_eng":"هدى محمد علي","name_arabic":"Huda Mohammed Ali","dob":"2014-08-15","date_of_birth":"2014-08-15","unified_id":"E26","passport_no":"AE11009988","passport":"AE11009988","contact_no":"+971502678901","nationality":"UAE","gender":"F","sex":"F","national_id":"784-2014-1100998-2","kin":"daughter","person_type":"citizen"},
            # Child from current wife (E24 - Sana)
            {"id":"E27","label":"Khalid Mohammed","full_name":"Khalid Mohammed Ali (son of Sana)","name_eng":"Khalid Mohammed Ali","name_arabic":"خالد محمد علي","dob":"2018-11-22","date_of_birth":"2018-11-22","unified_id":"E27","passport_no":"AE00998877","passport":"AE00998877","contact_no":"+971502789012","nationality":"UAE","gender":"M","sex":"M","national_id":"784-2018-0099887-1","kin":"son","person_type":"citizen"}
        ],
        "edges": [
            # Ego to parents
            {"source":"E20","target":"E21","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E20","target":"E22","type":"CHILD_OF","parent_sex":"F"},
            # Children from first wife - Layla (E23) - DIVORCED
            {"source":"E25","target":"E20","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E25","target":"E23","type":"CHILD_OF","parent_sex":"F"},
            {"source":"E26","target":"E20","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E26","target":"E23","type":"CHILD_OF","parent_sex":"F"},
            # Child from second wife - Sana (E24) - CURRENT
            {"source":"E27","target":"E20","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E27","target":"E24","type":"CHILD_OF","parent_sex":"F"},
            # Spouse relationships
            {"source":"E20","target":"E23","type":"SPOUSE_OF","relationship_status":"inactive"},
            {"source":"E20","target":"E24","type":"SPOUSE_OF","relationship_status":"active"},
            # Sibling relationships (children from same mother)
            {"source":"E25","target":"E26","type":"SIBLING_OF"}
        ],
        "generated_at": NOW
    },
    
    # E30: Complex family with grandparents and grandchildren
    "E30": {
        "root": "E30",
        "nodes": [
            {"id":"E30","label":"Saeed Omar","full_name":"Saeed Omar Al Zaabi","name_eng":"Saeed Omar Al Zaabi","name_arabic":"سعيد عمر الزعابي","dob":"1983-02-10","date_of_birth":"1983-02-10","unified_id":"E30","passport_no":"AE11223344","passport":"AE11223344","contact_no":"+971503012345","nationality":"UAE","gender":"M","sex":"M","national_id":"784-1983-1122334-1","kin":"self","person_type":"citizen"},
            {"id":"E31","label":"Omar Rashid","full_name":"Omar Rashid Al Zaabi","name_eng":"Omar Rashid Al Zaabi","name_arabic":"عمر راشد الزعابي","dob":"1958-05-20","date_of_birth":"1958-05-20","unified_id":"E31","passport_no":"AE22334455","passport":"AE22334455","contact_no":"+971503123456","nationality":"UAE","gender":"M","sex":"M","national_id":"784-1958-2233445-1","kin":"father","person_type":"citizen"},
            {"id":"E32","label":"Amina Omar","full_name":"Amina Omar Al Zaabi","name_eng":"Amina Omar Al Zaabi","name_arabic":"أمينة عمر الزعابي","dob":"1960-08-15","date_of_birth":"1960-08-15","unified_id":"E32","passport_no":"AE33445566","passport":"AE33445566","contact_no":"+971503234567","nationality":"UAE","gender":"F","sex":"F","national_id":"784-1960-3344556-2","kin":"mother","person_type":"citizen"},
            {"id":"E33","label":"Rashid Saeed","full_name":"Rashid Saeed Al Zaabi","name_eng":"Rashid Saeed Al Zaabi","name_arabic":"راشد سعيد الزعابي","dob":"1935-11-30","date_of_birth":"1935-11-30","unified_id":"E33","passport_no":"AE44556677","passport":"AE44556677","contact_no":"+971503345678","nationality":"UAE","gender":"M","sex":"M","national_id":"784-1935-4455667-1","kin":"paternal grandfather","person_type":"citizen"},
            {"id":"E34","label":"Fatima Rashid","full_name":"Fatima Rashid Al Zaabi","name_eng":"Fatima Rashid Al Zaabi","name_arabic":"فاطمة راشد الزعابي","dob":"1938-04-12","date_of_birth":"1938-04-12","unified_id":"E34","passport_no":"AE55667788","passport":"AE55667788","contact_no":"+971503456789","nationality":"UAE","gender":"F","sex":"F","national_id":"784-1938-5566778-2","kin":"paternal grandmother","person_type":"citizen"},
            {"id":"E35","label":"Mohammed Amina","full_name":"Mohammed Amina Al Nuaimi","name_eng":"Mohammed Amina Al Nuaimi","name_arabic":"محمد أمينة النعيمي","dob":"1933-07-25","date_of_birth":"1933-07-25","unified_id":"E35","passport_no":"AE66778899","passport":"AE66778899","contact_no":"+971503567890","nationality":"UAE","gender":"M","sex":"M","national_id":"784-1933-6677889-1","kin":"maternal grandfather","person_type":"citizen"},
            {"id":"E36","label":"Khadija Mohammed","full_name":"Khadija Mohammed Al Nuaimi","name_eng":"Khadija Mohammed Al Nuaimi","name_arabic":"خديجة محمد النعيمي","dob":"1936-10-08","date_of_birth":"1936-10-08","unified_id":"E36","passport_no":"AE77889900","passport":"AE77889900","contact_no":"+971503678901","nationality":"UAE","gender":"F","sex":"F","national_id":"784-1936-7788990-2","kin":"maternal grandmother","person_type":"citizen"},
            {"id":"E37","label":"Noor Saeed","full_name":"Noor Saeed Al Zaabi","name_eng":"Noor Saeed Al Zaabi","name_arabic":"نور سعيد الزعابي","dob":"1985-01-18","date_of_birth":"1985-01-18","unified_id":"E37","passport_no":"AE88990011","passport":"AE88990011","contact_no":"+971503789012","nationality":"UAE","gender":"F","sex":"F","national_id":"784-1985-8899001-2","kin":"wife","person_type":"citizen"},
            {"id":"E38","label":"Yusuf Saeed","full_name":"Yusuf Saeed Omar","name_eng":"Yusuf Saeed Omar","name_arabic":"يوسف سعيد عمر","dob":"2008-06-22","date_of_birth":"2008-06-22","unified_id":"E38","passport_no":"AE99001122","passport":"AE99001122","contact_no":"+971503890123","nationality":"UAE","gender":"M","sex":"M","national_id":"784-2008-9900112-1","kin":"son","person_type":"citizen"},
            {"id":"E39","label":"Layla Saeed","full_name":"Layla Saeed Omar","name_eng":"Layla Saeed Omar","name_arabic":"ليلى سعيد عمر","dob":"2010-09-14","date_of_birth":"2010-09-14","unified_id":"E39","passport_no":"AE00112233","passport":"AE00112233","contact_no":"+971503901234","nationality":"UAE","gender":"F","sex":"F","national_id":"784-2010-0011223-2","kin":"daughter","person_type":"citizen"},
            {"id":"E40","label":"Ahmed Yusuf","full_name":"Ahmed Yusuf Saeed","name_eng":"Ahmed Yusuf Saeed","name_arabic":"أحمد يوسف سعيد","dob":"2025-03-05","date_of_birth":"2025-03-05","unified_id":"E40","passport_no":"AE11223344","passport":"AE11223344","contact_no":"+971504012345","nationality":"UAE","gender":"M","sex":"M","national_id":"784-2025-1122334-1","kin":"grandson","person_type":"citizen"},
            {"id":"E41","label":"Mariam Yusuf","full_name":"Mariam Yusuf Saeed","name_eng":"Mariam Yusuf Saeed","name_arabic":"مريم يوسف سعيد","dob":"2027-07-20","date_of_birth":"2027-07-20","unified_id":"E41","passport_no":"AE22334455","passport":"AE22334455","contact_no":"+971504123456","nationality":"UAE","gender":"F","sex":"F","national_id":"784-2027-2233445-2","kin":"granddaughter","person_type":"citizen"},
            {"id":"E42","label":"Hassan Saeed","full_name":"Hassan Saeed Omar","name_eng":"Hassan Saeed Omar","name_arabic":"حسن سعيد عمر","dob":"1985-12-03","date_of_birth":"1985-12-03","unified_id":"E42","passport_no":"AE33445566","passport":"AE33445566","contact_no":"+971504234567","nationality":"UAE","gender":"M","sex":"M","national_id":"784-1985-3344556-1","kin":"brother","person_type":"citizen"}
        ],
        "edges": [
            # Ego to parents
            {"source":"E30","target":"E31","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E30","target":"E32","type":"CHILD_OF","parent_sex":"F"},
            # Parents to grandparents
            {"source":"E31","target":"E33","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E31","target":"E34","type":"CHILD_OF","parent_sex":"F"},
            {"source":"E32","target":"E35","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E32","target":"E36","type":"CHILD_OF","parent_sex":"F"},
            # Ego to children
            {"source":"E38","target":"E30","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E38","target":"E37","type":"CHILD_OF","parent_sex":"F"},
            {"source":"E39","target":"E30","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E39","target":"E37","type":"CHILD_OF","parent_sex":"F"},
            # Children to grandchildren
            {"source":"E40","target":"E38","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E41","target":"E38","type":"CHILD_OF","parent_sex":"F"},
            # Sibling
            {"source":"E42","target":"E31","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E42","target":"E32","type":"CHILD_OF","parent_sex":"F"},
            # Spouse
            {"source":"E30","target":"E37","type":"SPOUSE_OF","relationship_status":"active"},
            # Sibling relationships
            {"source":"E30","target":"E42","type":"SIBLING_OF"},
            {"source":"E38","target":"E39","type":"SIBLING_OF"},
            {"source":"E40","target":"E41","type":"SIBLING_OF"}
        ],
        "generated_at": NOW
    },
    
    # E40: Resident scenario (different person type)
    "E40": {
        "root": "E40",
        "nodes": [
            {"id":"E40","label":"John Smith","full_name":"John Smith","name_eng":"John Smith","name_arabic":"جون سميث","dob":"1985-03-15","date_of_birth":"1985-03-15","unified_id":"E40","passport_no":"US12345678","passport":"US12345678","contact_no":"+971504345678","nationality":"USA","gender":"M","sex":"M","national_id":None,"kin":"self","person_type":"resident"},
            {"id":"E41","label":"Sarah Smith","full_name":"Sarah Smith","name_eng":"Sarah Smith","name_arabic":"سارة سميث","dob":"1987-07-22","date_of_birth":"1987-07-22","unified_id":"E41","passport_no":"US87654321","passport":"US87654321","contact_no":"+971504456789","nationality":"USA","gender":"F","sex":"F","national_id":None,"kin":"wife","person_type":"resident"},
            {"id":"E42","label":"Emma Smith","full_name":"Emma Smith","name_eng":"Emma Smith","name_arabic":"إيما سميث","dob":"2012-11-08","date_of_birth":"2012-11-08","unified_id":"E42","passport_no":"US11223344","passport":"US11223344","contact_no":"+971504567890","nationality":"USA","gender":"F","sex":"F","national_id":None,"kin":"daughter","person_type":"resident"},
            {"id":"E43","label":"James Smith","full_name":"James Smith","name_eng":"James Smith","name_arabic":"جيمس سميث","dob":"2015-04-30","date_of_birth":"2015-04-30","unified_id":"E43","passport_no":"US22334455","passport":"US22334455","contact_no":"+971504678901","nationality":"USA","gender":"M","sex":"M","national_id":None,"kin":"son","person_type":"resident"}
        ],
        "edges": [
            {"source":"E42","target":"E40","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E42","target":"E41","type":"CHILD_OF","parent_sex":"F"},
            {"source":"E43","target":"E40","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E43","target":"E41","type":"CHILD_OF","parent_sex":"F"},
            {"source":"E40","target":"E41","type":"SPOUSE_OF","relationship_status":"active"},
            {"source":"E42","target":"E43","type":"SIBLING_OF"}
        ],
        "generated_at": NOW
    },
    
    # E50: Single person with no spouse
    "E50": {
        "root": "E50",
        "nodes": [
            {"id":"E50","label":"Khalid Ahmed","full_name":"Khalid Ahmed Al Mansoori","name_eng":"Khalid Ahmed Al Mansoori","name_arabic":"خالد أحمد المنصوري","dob":"1995-10-05","date_of_birth":"1995-10-05","unified_id":"E50","passport_no":"AE99887766","passport":"AE99887766","contact_no":"+971505012345","nationality":"UAE","gender":"M","sex":"M","national_id":"784-1995-9988776-1","kin":"self","person_type":"citizen"},
            {"id":"E51","label":"Ahmed Salim","full_name":"Ahmed Salim Al Mansoori","name_eng":"Ahmed Salim Al Mansoori","name_arabic":"أحمد سليم المنصوري","dob":"1970-12-18","date_of_birth":"1970-12-18","unified_id":"E51","passport_no":"AE88776655","passport":"AE88776655","contact_no":"+971505123456","nationality":"UAE","gender":"M","sex":"M","national_id":"784-1970-8877665-1","kin":"father","person_type":"citizen"},
            {"id":"E52","label":"Fatima Ahmed","full_name":"Fatima Ahmed Al Mansoori","name_eng":"Fatima Ahmed Al Mansoori","name_arabic":"فاطمة أحمد المنصوري","dob":"1973-05-25","date_of_birth":"1973-05-25","unified_id":"E52","passport_no":"AE77665544","passport":"AE77665544","contact_no":"+971505234567","nationality":"UAE","gender":"F","sex":"F","national_id":"784-1973-7766554-2","kin":"mother","person_type":"citizen"},
            {"id":"E53","label":"Omar Khalid","full_name":"Omar Khalid Ahmed","name_eng":"Omar Khalid Ahmed","name_arabic":"عمر خالد أحمد","dob":"2020-08-12","date_of_birth":"2020-08-12","unified_id":"E53","passport_no":"AE66554433","passport":"AE66554433","contact_no":"+971505345678","nationality":"UAE","gender":"M","sex":"M","national_id":"784-2020-6655443-1","kin":"son","person_type":"citizen"},
            {"id":"E54","label":"Layla Khalid","full_name":"Layla Khalid Ahmed","name_eng":"Layla Khalid Ahmed","name_arabic":"ليلى خالد أحمد","dob":"2022-01-20","date_of_birth":"2022-01-20","unified_id":"E54","passport_no":"AE55443322","passport":"AE55443322","contact_no":"+971505456789","nationality":"UAE","gender":"F","sex":"F","national_id":"784-2022-5544332-2","kin":"daughter","person_type":"citizen"}
        ],
        "edges": [
            {"source":"E50","target":"E51","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E50","target":"E52","type":"CHILD_OF","parent_sex":"F"},
            {"source":"E53","target":"E50","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E54","target":"E50","type":"CHILD_OF","parent_sex":"M"},
            {"source":"E53","target":"E54","type":"SIBLING_OF"}
        ],
        "generated_at": NOW
    }
}

@app.get("/api/v1/persons/{person_id}/exists")
def check_person_exists(person_id: str):
    """
    Check if a person with the given Unified ID exists in the database.
    """
    # Check if person exists in mock data
    exists = person_id in MOCK_GRAPH
    
    if not exists:
        return {"exists": False, "person_type": None}
    
    # Determine person type from the root node
    data = MOCK_GRAPH[person_id]
    root_node = next((n for n in data["nodes"] if n["id"] == person_id), None)
    person_type = root_node.get("person_type", "citizen") if root_node else "citizen"
    
    return {"exists": True, "person_type": person_type}

@app.get("/api/v1/persons/{person_id}/tree")
def get_tree(person_id: str, depth: int = 3, lang: str = "en"):
    data = MOCK_GRAPH.get(person_id)
    if not data:
        return {"root": person_id, "nodes": [], "edges": [], "generated_at": time.time()}
    return data

@app.get("/api/v1/lca")
def lca(personA: str, personB: str):
    # MOCK only
    return {"lcas": ["E2"] if personA == "E1" and personB == "E7" else []}

@app.post("/api/v1/infer")
def infer(payload: Dict[str, Any]):
    pid = payload.get("person_id")
    return {"person_id": pid, "candidates": [{"type":"parent","target":"E2","score":0.76,"explanation":"Shared surname + age gap"}]}

@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "FamilyTree API"}

@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    """Database health check endpoint"""
    try:
        # Test database connection
        user_count = db.query(UserDB).count()
        return {
            "status": "ok",
            "database": "connected",
            "users_count": user_count,
            "database_url": str(engine.url).replace(engine.url.password or "", "***") if engine.url.password else str(engine.url)
        }
    except Exception as e:
        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e)
        }

# Include routers
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(user_management.router)
