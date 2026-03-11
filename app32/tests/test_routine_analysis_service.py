from services.routine_analysis_service import _build_employee_drilldown, _apply_employee_filters


def test_apply_employee_filters_restricts_to_single_employee():
    employees = [
        {"id": 50, "name": "Quesia Prazeres", "department": "Adm/Fin"},
        {"id": 51, "name": "Outro Colaborador", "department": "Adm/Fin"},
    ]

    filtered = _apply_employee_filters(employees, employee_id=50)

    assert [employee["id"] for employee in filtered] == [50]



def test_build_employee_drilldown_tolerates_incomplete_meeting_payload():
    employee_by_id = {
        50: {
            "id": 50,
            "name": "Quesia Prazeres",
            "department": "Adm/Fin",
            "email": "quesia@example.com",
        }
    }

    result = _build_employee_drilldown(
        employee_id=50,
        employee_by_id=employee_by_id,
        routine_section={"all_routines": []},
        project_section={"member_allocations": []},
        process_section={"member_allocations": []},
        meeting_section={
            "meeting_details": [
                {
                    "id": 99,
                    "matched_employee_ids": [50],
                    # payload incompleto para simular dado legado/malformado
                }
            ]
        },
    )

    assert result is not None
    assert result["employee"]["id"] == 50
    assert result["meetings"] == [
        {
            "id": 99,
            "title": "Reunião",
            "project_name": "Sem projeto vinculado",
            "scheduled_date": None,
            "scheduled_time": None,
            "estimated_hours": 0.0,
            "duration_source": "heuristic",
        }
    ]
