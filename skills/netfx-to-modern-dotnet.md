# Skill: .NET Framework -> modern .NET (6/8/10)
- Convert csproj to SDK-style (`<Project Sdk="Microsoft.NET.Sdk">`), `<TargetFramework>` = target.
  Move packages.config -> PackageReference. Remove AssemblyInfo duplicates
  (`GenerateAssemblyInfo` false if AssemblyInfo.cs is kept).
- Prefer class libraries as `net<target>`; use `netstandard2.0` ONLY if another still-legacy
  consumer needs it.
- Replace removed APIs: System.Configuration (use System.Configuration.ConfigurationManager
  package for drop-in), System.Drawing (System.Drawing.Common, Windows only), AppDomain
  isolation, Remoting, BinaryFormatter (replace with System.Text.Json and note risk).
- Entity Framework 6 -> keep EF6 (supports .NET 6+) unless asked; do not switch to EF Core.
- WCF server -> CoreWCF; WCF client -> System.ServiceModel.* packages.
- Build and run `dotnet build`; fix analyzer errors but do not suppress them globally.
