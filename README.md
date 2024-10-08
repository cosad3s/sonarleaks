# Sonarleaks

<img src="assets/logo.jpg" alt="drawing" width="100"/>

## Summary

SonarCloud is a SAST SaaS platform built onto SonarQube.

During my DevSecOps journey, I recently discovered that [Sonarcloud](https://sonarcloud.io/) (From SonarSource) offers the possibility to explore public projects.
After working on [Postleaks](https://github.com/cosad3s/postleaks) and popularity of some other similars projects (like [swaggerHole](https://github.com/Liodeus/swaggerHole)) related to public data on SaaS, the `Explore` button triggers my curiosity.

I created this small tool to get basic infos about Sonarcloud projects from the Explore tab.   

**The results from SonarCloud are all marked as public projects, but appear to be related to private source repositories unrelated to SonarCloud. This could be the result of a misconfiguration on the customer side or something intentionally left public.**  
*Reminder: paying SonarCloud customers can [change the visibility](https://docs.sonarsource.com/sonarcloud/administering-sonarcloud/managing-organizations/#allow-only-private-projects) of their projects at any time.*

![alt text](assets/meme.jpg)

## Usage

```bash
❯ sonarleaks -h
usage: sonarleaks [-h] [--top] [--loc LOC] [-k KEYWORD] [-kf KEYWORD_FILE] [--private] [--source]

Sonarleaks 🛰️💧 Search for private code published to Sonarcloud.

options:
  -h, --help        show this help message and exit
  --top             Filter on top public projects
  --loc LOC         Filter on minimum of lines of code
  -k KEYWORD        Keyword (company, project, etc.)
  -kf KEYWORD_FILE  Keywords file
  --private         Only display components linked to potential private repository.
  --source          Only display components with available source code.
```

### Examples

***Top public projects, with minimum 500000 lines of code, with private repository and source code available***

`❯ sonarleaks --top --loc 500000 --source --private`

![alt text](assets/image.png)

***Projects related to keyword `Salesforce`***

`❯ sonarleaks -k salesforce`

![alt text](assets/image2.png)
