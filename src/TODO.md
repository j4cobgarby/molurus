# TODO list

### ~~Adapt the database and the API to use API tokens instead of session logon.~~

~~Currently the API is entirely based around HTTP sessions/cookies. This was a design
problem from the start which I didn't think about. It would clearly be much better
if instead of verifying permissions, etc., an API token was used, and then each token
would be assigned certain permissions. Each token would also be linked with a user
account.~~

**Done.**

### Generally clean up the code.

It's really messy in some parts.

**Partially done, but it's an ongoing process really.**

### Implement more API functions.

 - Friend requests
 - Settings users' preferred colour schemes
 - Returning path to user's profile picture, maybe? That might be useful.
