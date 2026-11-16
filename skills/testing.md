# Skill: characterization unit tests (xUnit)
- Create `<Project>.Tests` (xUnit, Microsoft.NET.Test.Sdk, xunit.runner.visualstudio) in /tests or
  next to the project, targeting the migrated framework. Add to the .sln.
- Test existing behaviour: public methods, boundary values, null/empty inputs, exceptions,
  and serialization output. Use Moq/NSubstitute for I/O boundaries.
- Tests must pass against the code as it is. If a test reveals a bug, assert the CURRENT
  behaviour and note it in MIGRATION_NOTES.md; never "fix" production code here.
- Run `dotnet test`; fix only test code until green.
