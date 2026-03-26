---
name: sf-integration
description: "Reference for Salesforce integration metadata — Named Credentials, Remote Site Settings, CSP Trusted Sites, External Data Sources, and Connected Apps. Includes Tooling API queries, XML structures, and security patterns."
---

# Salesforce Integration Skill

This skill provides comprehensive reference for Salesforce integration metadata types
including secure credential management, outbound callout configuration, content security
policies, external data connectivity, and OAuth-based application integrations.

---

## 1. Named Credentials

Named Credentials securely store authentication information for external service callouts.
They abstract endpoint URLs and credentials away from Apex code, improving security and
maintainability.

### Tooling API Query

```sql
SELECT Id, DeveloperName, MasterLabel, Endpoint,
       LastModifiedDate, LastModifiedBy.Name
FROM NamedCredential
WHERE NamespacePrefix = null
ORDER BY DeveloperName
```

**API:** Tooling API

### File Structure

```
force-app/main/default/namedCredentials/
  {Name}.namedCredential-meta.xml
```

### Legacy Named Credential XML (pre-API v58)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<NamedCredential xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>My External Service</label>
    <allowMergeFieldsInBody>false</allowMergeFieldsInBody>
    <allowMergeFieldsInHeader>true</allowMergeFieldsInHeader>
    <endpoint>https://api.example.com</endpoint>
    <generateAuthorizationHeader>true</generateAuthorizationHeader>
    <oauthRefreshToken/>
    <oauthScope/>
    <oauthToken/>
    <password/>
    <principalType>NamedUser</principalType>
    <protocol>Password</protocol>
    <username>api-user@example.com</username>
</NamedCredential>
```

### New Named Credential + External Credential (API v58+)

Starting with API v58, Salesforce split Named Credentials into two parts:

- **External Credential:** Stores the authentication protocol and credentials
- **Named Credential:** Stores the endpoint URL and references an External Credential

```
force-app/main/default/externalCredentials/
  {Name}.externalCredential-meta.xml

force-app/main/default/namedCredentials/
  {Name}.namedCredential-meta.xml
```

External Credential XML:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ExternalCredential xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>My External Credential</label>
    <authenticationProtocol>Custom</authenticationProtocol>
    <externalCredentialParameters>
        <parameterName>ApiKey</parameterName>
        <parameterType>AuthHeader</parameterType>
        <parameterValue>Bearer {!$Credential.MyExternalCred.ApiKey}</parameterValue>
    </externalCredentialParameters>
</ExternalCredential>
```

New-style Named Credential XML:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<NamedCredential xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>My External Service</label>
    <endpoint>https://api.example.com</endpoint>
    <externalCredential>My_External_Credential</externalCredential>
    <allowMergeFieldsInBody>false</allowMergeFieldsInBody>
    <allowMergeFieldsInHeader>true</allowMergeFieldsInHeader>
    <generateAuthorizationHeader>true</generateAuthorizationHeader>
</NamedCredential>
```

### Usage in Apex

```java
HttpRequest req = new HttpRequest();
req.setEndpoint('callout:My_Named_Credential/api/v1/records');
req.setMethod('GET');
req.setHeader('Content-Type', 'application/json');

Http http = new Http();
HttpResponse res = http.send(req);

if (res.getStatusCode() == 200) {
    Map<String, Object> result = (Map<String, Object>) JSON.deserializeUntyped(res.getBody());
}
```

The `callout:` prefix tells Salesforce to use the Named Credential for the endpoint URL
and to inject the stored authentication headers automatically.

### Security Benefits

- Credentials are never stored in Apex code or custom settings
- Endpoint URLs can change without code changes (just update the Named Credential)
- Per-user or per-profile credential assignment via External Credentials
- Automatic token refresh for OAuth-based Named Credentials
- Auditable via Setup > Named Credentials

### Deploy Named Credentials

```bash
sf project deploy start \
  --source-dir force-app/main/default/namedCredentials/{Name}.namedCredential-meta.xml \
  --target-org <alias>
```

Note: Credentials (passwords, tokens) are NOT included in metadata deployments.
After deploying, configure credentials manually in Setup or via the CLI.

---

## 2. Remote Site Settings

Remote Site Settings whitelist external endpoints for outbound HTTP callouts from Apex.
Any Apex HTTP callout to an endpoint NOT covered by a Named Credential requires a
Remote Site Setting.

### Tooling API Query

The Tooling API object for Remote Site Settings is `RemoteProxy`:

```sql
SELECT Id, SiteName, EndpointUrl, IsActive,
       LastModifiedDate, LastModifiedBy.Name
FROM RemoteProxy
WHERE NamespacePrefix = null
ORDER BY SiteName
```

_Note: `DeveloperName` is NOT a valid field on `RemoteProxy` in Tooling API — use `SiteName` as the identifier instead._

**API:** Tooling API

### File Structure

```
force-app/main/default/remoteSiteSettings/
  {Name}.remoteSite-meta.xml
```

### Meta XML Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<RemoteSiteSetting xmlns="http://soap.sforce.com/2006/04/metadata">
    <disableProtocolSecurity>false</disableProtocolSecurity>
    <isActive>true</isActive>
    <url>https://api.example.com</url>
    <description>External API for data synchronization</description>
</RemoteSiteSetting>
```

### Key Points

- Required for any direct `HttpRequest` callout (not using Named Credentials)
- The URL must match the protocol (https) and domain of the callout endpoint
- Subpaths are automatically allowed — registering `https://api.example.com` allows
  callouts to `https://api.example.com/v1/records` and any other path
- `disableProtocolSecurity` should remain `false` in production (enforces HTTPS)
- Inactive Remote Site Settings block callouts to that endpoint

### Deploy Remote Site Settings

```bash
sf project deploy start \
  --source-dir force-app/main/default/remoteSiteSettings/{Name}.remoteSite-meta.xml \
  --target-org <alias>
```

---

## 3. CSP Trusted Sites

Content Security Policy (CSP) Trusted Sites allow Lightning components (LWC and Aura)
to load external resources such as scripts, images, stylesheets, or make client-side
API calls (fetch/XHR).

### Tooling API Query

```sql
SELECT Id, DeveloperName, EndpointUrl, IsActive, Context,
       LastModifiedDate, LastModifiedBy.Name
FROM CspTrustedSite
WHERE NamespacePrefix = null
ORDER BY DeveloperName
```

**API:** Tooling API

### File Structure

```
force-app/main/default/cspTrustedSites/
  {Name}.cspTrustedSite-meta.xml
```

### Meta XML Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CspTrustedSite xmlns="http://soap.sforce.com/2006/04/metadata">
    <endpointUrl>https://cdn.example.com</endpointUrl>
    <isActive>true</isActive>
    <context>All</context>
    <description>CDN for external JavaScript libraries</description>
    <isApplicableToConnectSrc>true</isApplicableToConnectSrc>
    <isApplicableToFontSrc>false</isApplicableToFontSrc>
    <isApplicableToFrameSrc>false</isApplicableToFrameSrc>
    <isApplicableToImgSrc>true</isApplicableToImgSrc>
    <isApplicableToMediaSrc>false</isApplicableToMediaSrc>
    <isApplicableToStyleSrc>true</isApplicableToStyleSrc>
</CspTrustedSite>
```

### CSP Directive Flags

| Flag | Purpose | Example |
|---|---|---|
| `isApplicableToConnectSrc` | Allow fetch/XHR requests | API calls from LWC |
| `isApplicableToFontSrc` | Allow loading fonts | Custom font CDN |
| `isApplicableToFrameSrc` | Allow iframe embedding | Embedded external content |
| `isApplicableToImgSrc` | Allow loading images | External image hosting |
| `isApplicableToMediaSrc` | Allow loading audio/video | Media streaming |
| `isApplicableToStyleSrc` | Allow loading stylesheets | External CSS CDN |

### Context Values

| Context | Description |
|---|---|
| `All` | Trusted in all contexts |
| `LEX` | Lightning Experience only |
| `Communities` | Experience Cloud sites only |
| `VisualForce` | Visualforce pages only |

### When CSP Trusted Sites Are Required

- LWC component makes a `fetch()` call to an external API
- LWC/Aura component loads an external JavaScript library via `<script>`
- Component displays images from an external domain
- Component embeds external content in an iframe

### Important Notes

- CSP Trusted Sites are for CLIENT-SIDE requests from Lightning components
- Remote Site Settings are for SERVER-SIDE requests from Apex
- Both may be needed if a component calls Apex which calls an external API AND the
  component also makes direct client-side calls

### Deploy CSP Trusted Sites

```bash
sf project deploy start \
  --source-dir force-app/main/default/cspTrustedSites/{Name}.cspTrustedSite-meta.xml \
  --target-org <alias>
```

---

## 4. External Data Sources

External Data Sources connect Salesforce to external databases and APIs, exposing
external data as virtual (read-only or read-write) Salesforce objects via
Salesforce Connect (formerly Lightning Connect).

### Tooling API Query

```sql
SELECT Id, DeveloperName, MasterLabel, Type,
       LastModifiedDate, LastModifiedBy.Name
FROM ExternalDataSource
WHERE NamespacePrefix = null
ORDER BY DeveloperName
```

**API:** Tooling API

### File Structure

```
force-app/main/default/externalDataSources/
  {Name}.externalDataSource-meta.xml
```

### Types of External Data Sources

| Type | Description |
|---|---|
| OData 2.0 / 4.0 | Connect to OData-compliant APIs |
| Salesforce Connect: Cross-Org | Connect to another Salesforce org |
| Salesforce Connect: Custom (Apex) | Custom adapter via Apex `DataSource.Provider` |
| Simple URL | Basic URL-based data source |

### Meta XML Example (OData)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ExternalDataSource xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>External ERP</label>
    <type>OData4</type>
    <endpoint>https://erp.example.com/odata/v4</endpoint>
    <principalType>NamedUser</principalType>
    <protocol>Password</protocol>
    <isWritable>false</isWritable>
</ExternalDataSource>
```

### External Objects

Once an External Data Source is configured, Salesforce creates External Objects
(suffix `__x`) that map to the external tables/entities:

- External Objects appear in the object list but data lives externally
- Support SOQL queries (translated to external API calls)
- Can participate in relationships with standard/custom objects via External Lookup fields
- Indirect Lookup and External Lookup relationship field types

### Deploy External Data Sources

```bash
sf project deploy start \
  --source-dir force-app/main/default/externalDataSources/{Name}.externalDataSource-meta.xml \
  --target-org <alias>
```

---

## 5. Connected Apps

Connected Apps configure OAuth-based integrations for external applications to
authenticate with Salesforce. They define OAuth scopes, callback URLs, and
access policies.

### Retrieval

Connected Apps are NOT fully queryable via Tooling API SOQL. Use metadata retrieve:

```bash
sf project retrieve start --metadata "ConnectedApp" --target-org <alias>
```

To retrieve a specific Connected App:

```bash
sf project retrieve start --metadata "ConnectedApp:My_Connected_App" --target-org <alias>
```

### File Structure

```
force-app/main/default/connectedApps/
  {Name}.connectedApp-meta.xml
```

### Meta XML Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ConnectedApp xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>My Integration App</label>
    <contactEmail>admin@example.com</contactEmail>
    <oauthConfig>
        <callbackUrl>https://app.example.com/callback</callbackUrl>
        <consumerKey>3MVG9...</consumerKey>
        <isAdminApproved>false</isAdminApproved>
        <isConsumerSecretOptional>false</isConsumerSecretOptional>
        <isIntrospectAllTokens>false</isIntrospectAllTokens>
        <scopes>Api</scopes>
        <scopes>RefreshToken</scopes>
        <scopes>Web</scopes>
    </oauthConfig>
    <oauthPolicy>
        <ipRelaxation>ENFORCE</ipRelaxation>
        <refreshTokenPolicy>infinite</refreshTokenPolicy>
    </oauthPolicy>
    <profileName>System Administrator</profileName>
</ConnectedApp>
```

### Common OAuth Scopes

| Scope | API Name | Description |
|---|---|---|
| API | `Api` | Access REST/SOAP APIs |
| Full access | `Full` | Full access to all data |
| Refresh token | `RefreshToken` | Allow refresh tokens |
| Web | `Web` | Access via web browser |
| OpenID | `OpenID` | OpenID Connect access |
| Custom permissions | `CustomPermissions` | Access custom permissions |

### Security Configuration

- **IP Relaxation:** Enforce IP restrictions, relax for refresh tokens, or relax fully
- **Session Policies:** Timeout, high-assurance session requirements
- **Permission Set Assignment:** Control which users can use the Connected App
- **Profile Assignment:** Alternative to permission sets for access control

### Deploy Connected Apps

```bash
sf project deploy start \
  --source-dir force-app/main/default/connectedApps/{Name}.connectedApp-meta.xml \
  --target-org <alias>
```

Note: Consumer secret is NOT included in metadata. Configure via Setup after deployment.

---

## 6. Auth Providers

Auth Providers enable external authentication (SSO) for Salesforce users or
Experience Cloud site users.

### Retrieval

```bash
sf project retrieve start --metadata "AuthProvider" --target-org <alias>
```

### File Structure

```
force-app/main/default/authproviders/
  {Name}.authprovider-meta.xml
```

### Supported Provider Types

| Type | Description |
|---|---|
| Salesforce | Another Salesforce org |
| Google | Google OAuth |
| Facebook | Facebook OAuth |
| OpenIdConnect | Any OpenID Connect provider |
| MicrosoftACS | Microsoft Azure ACS |
| LinkedIn | LinkedIn OAuth |
| Twitter | Twitter OAuth |
| Janrain | Janrain identity provider |
| Custom | Custom Apex `Auth.AuthProviderPlugin` |

### Meta XML Example (OpenID Connect)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<AuthProvider xmlns="http://soap.sforce.com/2006/04/metadata">
    <friendlyName>Corporate SSO</friendlyName>
    <providerType>OpenIdConnect</providerType>
    <authorizeUrl>https://idp.example.com/authorize</authorizeUrl>
    <tokenUrl>https://idp.example.com/token</tokenUrl>
    <userInfoUrl>https://idp.example.com/userinfo</userInfoUrl>
    <defaultScopes>openid profile email</defaultScopes>
    <consumerKey>client-id-here</consumerKey>
    <executionUser>admin@example.com</executionUser>
    <includeOrgIdInId>false</includeOrgIdInId>
    <sendAccessTokenInHeader>true</sendAccessTokenInHeader>
    <sendClientCredentialsInHeader>false</sendClientCredentialsInHeader>
</AuthProvider>
```

### Deploy Auth Providers

```bash
sf project deploy start \
  --source-dir force-app/main/default/authproviders/{Name}.authprovider-meta.xml \
  --target-org <alias>
```

---

## 7. Callout Patterns in Apex

### Named Credential Callout (Recommended)

```java
public class ExternalServiceCallout {

    public static Map<String, Object> getRecords() {
        HttpRequest req = new HttpRequest();
        req.setEndpoint('callout:My_Named_Credential/api/v2/records');
        req.setMethod('GET');
        req.setHeader('Accept', 'application/json');
        req.setTimeout(30000); // 30 seconds

        Http http = new Http();
        HttpResponse res = http.send(req);

        if (res.getStatusCode() != 200) {
            throw new CalloutException('Callout failed: ' + res.getStatusCode()
                                       + ' ' + res.getBody());
        }

        return (Map<String, Object>) JSON.deserializeUntyped(res.getBody());
    }
}
```

### Direct HTTP Callout (Requires Remote Site Setting)

```java
public class DirectCallout {

    public static String postData(String jsonBody) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint('https://api.example.com/v1/data');
        req.setMethod('POST');
        req.setHeader('Content-Type', 'application/json');
        req.setHeader('Authorization', 'Bearer ' + getToken());
        req.setBody(jsonBody);
        req.setTimeout(120000); // 120 seconds max

        Http http = new Http();
        HttpResponse res = http.send(req);

        return res.getBody();
    }
}
```

### Async Callout — Future Method

```java
public class AsyncCalloutService {

    @future(callout=true)
    public static void sendDataAsync(String recordId) {
        // Callout logic here
        HttpRequest req = new HttpRequest();
        req.setEndpoint('callout:My_Service/api/notify');
        req.setMethod('POST');
        req.setBody('{"recordId":"' + recordId + '"}');

        Http http = new Http();
        HttpResponse res = http.send(req);
    }
}
```

### Async Callout — Queueable

```java
public class CalloutQueueable implements Queueable, Database.AllowsCallouts {

    private List<String> recordIds;

    public CalloutQueueable(List<String> recordIds) {
        this.recordIds = recordIds;
    }

    public void execute(QueueableContext context) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint('callout:My_Service/api/batch');
        req.setMethod('POST');
        req.setHeader('Content-Type', 'application/json');
        req.setBody(JSON.serialize(recordIds));

        Http http = new Http();
        HttpResponse res = http.send(req);

        // Process response, chain next queueable if needed
    }
}
```

### Mock Pattern for Testing

```java
@isTest
public class MockHttpResponse implements HttpCalloutMock {

    private Integer statusCode;
    private String body;

    public MockHttpResponse(Integer statusCode, String body) {
        this.statusCode = statusCode;
        this.body = body;
    }

    public HttpResponse respond(HttpRequest req) {
        HttpResponse res = new HttpResponse();
        res.setStatusCode(this.statusCode);
        res.setBody(this.body);
        res.setHeader('Content-Type', 'application/json');
        return res;
    }
}

// In test method:
@isTest
static void testCallout() {
    Test.setMock(HttpCalloutMock.class, new MockHttpResponse(200, '{"status":"ok"}'));

    Test.startTest();
    Map<String, Object> result = ExternalServiceCallout.getRecords();
    Test.stopTest();

    System.assertNotEquals(null, result, 'Response should not be null');
}
```

---

## 8. Gotchas and Common Pitfalls

### Callout Limits

- **100 callouts per transaction** — this is a hard governor limit
- **Maximum timeout: 120 seconds** per callout (set via `req.setTimeout()`)
- **Maximum cumulative timeout: 120 seconds** for all callouts in a transaction
- **Maximum request/response size: 12 MB** (6 MB for synchronous Apex)
- Callout limits are per-transaction, not per-callout

### No Callouts in Triggers

- Apex triggers cannot make synchronous HTTP callouts
- Use `@future(callout=true)` or `Queueable` with `Database.AllowsCallouts` to
  perform callouts from trigger context
- Consider Platform Events for decoupled async processing

### Named Credentials vs Remote Site Settings

| Criteria | Named Credential | Remote Site Setting |
|---|---|---|
| Stores credentials | Yes | No |
| Auto-injects auth headers | Yes | No |
| Requires code changes for URL change | No | Yes |
| Per-user credentials | Yes (via External Credentials) | No |
| Required for direct HTTP callouts | No | Yes |
| Recommended | Yes, always | Only when Named Credential not feasible |

**Rule of thumb:** Always use Named Credentials. Use Remote Site Settings only when
you cannot use Named Credentials (e.g., dynamic endpoints, complex auth).

### CSP Requirements for LWC

- If an LWC component makes a client-side `fetch()` call, a CSP Trusted Site is required
- If Apex makes the callout on behalf of the LWC, only a Remote Site Setting (or Named
  Credential) is needed — no CSP Trusted Site required
- Loading external images in LWC `<img>` tags requires a CSP Trusted Site with `isApplicableToImgSrc`

### Connected App Security

- Consumer Secret is never included in metadata deployments
- Always configure IP restrictions in production
- Use Permission Sets (not Profiles) to control Connected App access when possible
- Rotate consumer secrets periodically
- Monitor Connected App usage via Login History and Event Monitoring

### Deployment Order for Integration Components

1. External Credentials (if using new-style Named Credentials)
2. Named Credentials
3. Remote Site Settings
4. CSP Trusted Sites
5. Connected Apps
6. Auth Providers
7. Apex classes that reference Named Credentials (callout classes)

---

## 9. Useful CLI Commands

### List Named Credentials

```bash
sf data query --query "SELECT DeveloperName, MasterLabel, Endpoint FROM NamedCredential WHERE NamespacePrefix = null ORDER BY DeveloperName" --target-org <alias> --use-tooling-api
```

### List Remote Site Settings

```bash
sf data query --query "SELECT SiteName, EndpointUrl, IsActive FROM RemoteProxy WHERE NamespacePrefix = null ORDER BY SiteName" --target-org <alias> --use-tooling-api
```

### List CSP Trusted Sites

```bash
sf data query --query "SELECT DeveloperName, EndpointUrl, IsActive, Context FROM CspTrustedSite WHERE NamespacePrefix = null ORDER BY DeveloperName" --target-org <alias> --use-tooling-api
```

### Retrieve All Integration Metadata

```bash
sf project retrieve start \
  --metadata "NamedCredential" \
  --metadata "RemoteSiteSetting" \
  --metadata "CspTrustedSite" \
  --metadata "ExternalDataSource" \
  --metadata "ConnectedApp" \
  --metadata "AuthProvider" \
  --target-org <alias>
```

---

## Context Specification

- metadata_type: NamedCredential, RemoteSiteSetting, CspTrustedSite, ExternalDataSource
- context_path: {alias}/integration/
- inventory_file: {alias}/integration/_inventory.md
- detail_file_pattern: {alias}/integration/{ApiName}.md

### Change Detection Queries

**Named Credentials**
Uses: tooling API
```sql
SELECT DeveloperName, MasterLabel, Endpoint,
       LastModifiedDate, LastModifiedBy.Name
FROM NamedCredential
WHERE NamespacePrefix = null
  AND LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

**Remote Site Settings**
Uses: tooling API
```sql
SELECT DeveloperName, SiteName, EndpointUrl, IsActive,
       LastModifiedDate, LastModifiedBy.Name
FROM RemoteProxy
WHERE NamespacePrefix = null
  AND LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

**CSP Trusted Sites**
Uses: tooling API
```sql
SELECT DeveloperName, EndpointUrl, IsActive, Context,
       LastModifiedDate, LastModifiedBy.Name
FROM CspTrustedSite
WHERE NamespacePrefix = null
  AND LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

**External Data Sources**
Uses: tooling API
```sql
SELECT DeveloperName, MasterLabel, Type,
       LastModifiedDate, LastModifiedBy.Name
FROM ExternalDataSource
WHERE NamespacePrefix = null
  AND LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

### Inventory Columns

| Type | API Name | Label | Endpoint/URL | Active | Last Modified | Modified By |
|---|---|---|---|---|---|---|

### Naming Convention Detection

- **Named Credentials:** PascalCase or underscore-separated (e.g., `My_External_API`, `PaymentGateway`)
- **Remote Site Settings:** Descriptive names matching service purpose (e.g., `External_ERP_API`)
- **CSP Trusted Sites:** Domain-based names (e.g., `CDN_Example_Com`, `Analytics_Provider`)
- **External Data Sources:** System or service names (e.g., `ERP_OData`, `Legacy_Database`)

### Detail File Sections

- Identity (API Name, Label, Type)
- Configuration (Endpoint URL, Authentication Protocol, Active Status)
- Security (IP Restrictions, OAuth Scopes, Session Policies)
- Dependencies (Apex Classes Using This Credential, Connected Components)
- Last Scanned Timestamp
