---
name: issue-brief
description: Fixed plain-English format for reporting any issue, blocker, or leftover work to the user.
---

# Issue Brief

Exists because side-issues surfaced mid-task used to pile up and blindside the user later (2026-08-13 directive).

## The rules

1. **One brief per issue.** Never mention an issue in passing. If it is
   worth saying, it gets the full template below. If it is not worth the
   template, do not raise it; fix it silently or drop it.
2. **Plain English first.** Assume the reader did NOT follow the session.
   Define every term of art in parentheses on first use ("medoid (the one
   representative day we picked for the month)"). No acronyms without
   expansion. No referring to internal codenames as if they explain
   themselves.
3. **Numbers carry meaning.** Never state a number without saying what it
   means for the user ("$0.25/bbl, about the bid/offer noise on a diff").
4. **Keep a running open-issues list** during any long task. When the user
   asks "what's left / remaining / anything else?", answer FROM that list,
   every item in short-brief form, including the ones you hoped to handle
   quietly. An issue the user learns about late is a failure even if it was
   fixed.
5. **The ask connection.** Every brief starts by saying how this issue
   connects to what the user originally asked for. If it doesn't connect,
   say plainly: "unrelated to your ask, found while working."

## The template

> **Issue:** one sentence, plain English, no jargon.
> **How it connects to your ask:** one sentence.
> **Why it matters:** what goes wrong for YOU if ignored (money, wrong
> numbers, broken page, wasted time). One or two sentences.
> **What's affected right now:** named pages / tables / decisions. State
> clearly if nothing is affected yet.
> **Root cause:** one or two sentences, plain English.
> **Fix options:** the realistic ones, one line each, with cost (time,
> nights, money).
> **My recommendation:** one option, one sentence of why.
> **What I need from you:** decision / nothing / a deadline. Never bury the
> ask.

## Scope

- Chat replies, reports, and summaries. Applies to newly found problems,
  failed checks, degraded results, deferred work, and anything the user
  will later discover changed.
- Does NOT apply to routine progress ("tests green", "deployed"). It applies only to
  things that are wrong, risky, deferred, or surprising.
